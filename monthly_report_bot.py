"""
월간 현황 보고서 봇 (AWS Lambda 버전)

이 하나의 Lambda 함수가 두 가지 트리거를 처리합니다.
1. API Gateway를 통한 Slack 이벤트/커맨드/모달 제출 (기존과 동일)
2. EventBridge 스케줄 규칙을 통한 정기 호출 -> 오늘이 "이번달 마지막주 수요일"이면
   지정 채널에 "월간보고 작성하기" 버튼 알림을 올림

EventBridge에서 오는 예약 이벤트는 기본적으로 "source": "aws.events" 를 포함하므로
그 필드로 두 트리거를 구분합니다.
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

import logging

from slack_bolt import App # Slack Bolt Framework의 Controller 역할(Router, Handler, API Client Mappper)
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

from report_config import (
    RECIPIENTS,
    DOORAY_DOMAIN,
)
from report_pdf import generate_report_pdf

# 1. 환경변수 설정
# AWS Lambda 환경변수에서 SLACK_BOT_TOKEN 필수 사용
BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN") 
# 반복 알림 시간 설정
REMINDER_HOUR = int(os.environ.get("REMINDER_HOUR", 9))
REMINDER_MINUTE = int(os.environ.get("REMINDER_MINUTE", 10))
REMINDER_TIMEZONE = os.environ.get("REMINDER_TIMEZONE", "Asia/Seoul")
# Slack 설정
REMINDER_CHANNEL_ID = os.environ.get("REMINDER_CHANNEL_ID")
SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")

if not BOT_TOKEN:
    print("환경변수 SLACK_BOT_TOKEN 을 설정해주세요.", file=sys.stderr)
    sys.exit(1)

logging.getLogger().setLevel(logging.INFO)

# Slack Bot 인증 정보 설정
app = App(
    token=BOT_TOKEN,
    signing_secret=SIGNING_SECRET,
    process_before_response=True
)

# 수신자 정보 설정
RECIPIENT_OPTIONS = [
    {"text": {"type": "plain_text", "text": name}, "value": email}
    for name, email in RECIPIENTS.items()
]

# Action Handler (버튼 클릭 등 인터랙션 처리)
@app.action("open_dooray_compose")
def handle_open_dooray_compose(ack):
    ack()

@app.action("open_report_modal_button")
def open_report_modal_via_button(ack, body, client):
    ack()
    client.views_open(trigger_id=body["trigger_id"], view=build_report_modal_view())

# Modal View 레이아웃 생성 함수
def build_report_modal_view():
    now = datetime.now()
    return {
        "type": "modal",
        "callback_id": "monthly_report_submit",
        "title": {"type": "plain_text", "text": "월간 현황 보고서"},
        "submit": {"type": "plain_text", "text": "생성 및 전송"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "period_block",
                "label": {"type": "plain_text", "text": "대상 년/월 (예: 2026-08)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "period_input",
                    "initial_value": now.strftime("%Y-%m"),
                },
            },
            {
                "type": "input",
                "block_id": "author_block",
                "label": {"type": "plain_text", "text": "작성자"},
                "element": {"type": "plain_text_input", "action_id": "author_input"},
            },
            {
                "type": "input",
                "block_id": "to_block",
                "label": {"type": "plain_text", "text": "수신자"},
                "element": {
                    "type": "static_select",
                    "action_id": "to_input",
                    "placeholder": {"type": "plain_text", "text": "수신자 선택"},
                    "options": RECIPIENT_OPTIONS,
                },
            },
            {
                "type": "input",
                "block_id": "cc_block",
                "label": {"type": "plain_text", "text": "참조자 (CC)"},
                "optional": True,
                "element": {
                    "type": "multi_static_select",
                    "action_id": "cc_input",
                    "placeholder": {"type": "plain_text", "text": "참조자 선택 (여러 명 가능)"},
                    "options": RECIPIENT_OPTIONS,
                },
            },
            {
                "type": "input",
                "block_id": "plan_this_block",
                "label": {"type": "plain_text", "text": "금월 계획"},
                "element": {"type": "plain_text_input", "action_id": "plan_this_input", "multiline": True},
            },
            {
                "type": "input",
                "block_id": "result_this_block",
                "label": {"type": "plain_text", "text": "금월 실적"},
                "element": {"type": "plain_text_input", "action_id": "result_this_input", "multiline": True},
            },
            {
                "type": "input",
                "block_id": "plan_next_block",
                "label": {"type": "plain_text", "text": "차월 계획"},
                "element": {"type": "plain_text_input", "action_id": "plan_next_input", "multiline": True},
            },
            {
                "type": "input",
                "block_id": "remark_block",
                "label": {"type": "plain_text", "text": "비고"},
                "optional": True,
                "element": {"type": "plain_text_input", "action_id": "remark_input", "multiline": True},
            },
            {
                "type": "input",
                "block_id": "issue_block",
                "label": {"type": "plain_text", "text": "애로 사항"},
                "optional": True,
                "element": {"type": "plain_text_input", "action_id": "issue_input", "multiline": True},
            },
            {
                "type": "input",
                "block_id": "request_block",
                "label": {"type": "plain_text", "text": "요청 및 전달 사항"},
                "optional": True,
                "element": {"type": "plain_text_input", "action_id": "request_input", "multiline": True},
            },
        ],
    }

# Slash Command
@app.command("/monthly_report")
def open_report_modal(ack, body, client):
    ack()
    client.views_open(trigger_id=body["trigger_id"], view=build_report_modal_view())

# Modal 제출
@app.view("monthly_report_submit")
def handle_report_submit(ack, client, body, view):
    ack()

    user_id = body["user"]["id"]
    values = view["state"]["values"]

    dm = client.conversations_open(users=[user_id])
    dm_channel_id = dm["channel"]["id"]

    period = values["period_block"]["period_input"]["value"] or datetime.now().strftime("%Y-%m")
    try:
        year_str, month_str = period.split("-")
        year, month = int(year_str), int(month_str)
    except ValueError:
        year, month = datetime.now().year, datetime.now().month

    author = values["author_block"]["author_input"]["value"] or "-"
    to_email = values["to_block"]["to_input"]["selected_option"]["value"]
    cc_selected = values["cc_block"]["cc_input"]["selected_options"] or []
    cc_emails = [opt["value"] for opt in cc_selected]

    plan_this = values["plan_this_block"]["plan_this_input"]["value"] or "-"
    result_this = values["result_this_block"]["result_this_input"]["value"] or "-"
    plan_next = values["plan_next_block"]["plan_next_input"]["value"] or "-"
    remark = values["remark_block"]["remark_input"]["value"] or ""
    issue = values["issue_block"]["issue_input"]["value"] or "특이사항 없음"
    request_text = values["request_block"]["request_input"]["value"] or "없음"

    filename = f"월간현황보고서_{year}년{month:02d}월_{author}.pdf"
    tmp_path = os.path.join(tempfile.gettempdir(), filename)
    generate_report_pdf(
        tmp_path,
        year=year,
        month=month,
        author=author,
        plan_this_month=plan_this,
        result_this_month=result_this,
        plan_next_month=plan_next,
        remark=remark,
        issues=issue,
        requests_text=request_text,
    )

    subject = f"{year}년 {month}월 월간 현황 보고서 ({author})"
    cc_text = ", ".join(cc_emails) if cc_emails else "없음"

    # 두레이 메일 쓰기창 딥링크 (제목/수신/참조 자동 입력)
    compose_url = (
        f"https://{DOORAY_DOMAIN}/mail/write/new"
        f"?subject={quote(subject)}"
        f"&to={quote(to_email)}"
    )
    if cc_emails:
        compose_url += f"&cc={quote(','.join(cc_emails))}"

    client.files_upload_v2(
        channel=dm_channel_id,
        file=tmp_path,
        filename=filename,
        initial_comment=(
            f"*{subject}* 파일이 생성됐어요.\n"
            "이 파일을 다운로드한 뒤, 아래 버튼으로 열리는 메일 쓰기창에 첨부해주세요. "
            "제목/수신/참조는 이미 채워져서 열려요."
        ),
    )

    client.chat_postMessage(
        channel=dm_channel_id,
        text="메일 작성창 열기",
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"수신자: {to_email}\n참조: {cc_text}\n제목: {subject}"},
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "메일 작성창 열기"},
                        "url": compose_url,
                        "style": "primary",
                        "action_id": "open_dooray_compose",
                    }
                ],
            },
        ],
    )

    os.remove(tmp_path)


# ==========================================
# 매월 마지막주 수요일 체크 + 알림 (EventBridge 트리거)
# ==========================================
def _is_last_wednesday(today):
    """today가 그 달의 마지막 수요일이면 True."""
    if today.weekday() != 2:  # 0=월요일 ... 2=수요일
        return False
    return (today + timedelta(days=7)).month != today.month


def post_monthly_reminder(force=False):
    tz = ZoneInfo(REMINDER_TIMEZONE)
    today = datetime.now(tz)

    if not force and not _is_last_wednesday(today):
        print(f"오늘({today.date()})은 마지막주 수요일이 아님 - 알림 건너뜀")
        return

    if not REMINDER_CHANNEL_ID:
        print("REMINDER_CHANNEL_ID 환경변수가 설정되지 않아 알림을 보낼 수 없습니다.", file=sys.stderr)
        return

    app.client.chat_postMessage(
        channel=REMINDER_CHANNEL_ID,
        text="이번달 월간보고를 작성해주세요.",
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*이번달 월간보고를 작성해주세요* :spiral_calendar_pad:"},
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "월간보고 작성하기"},
                        "action_id": "open_report_modal_button",
                        "style": "primary",
                    }
                ],
            },
        ],
    )
    print(f"[{today}] 월간보고 알림 게시 완료 (channel={REMINDER_CHANNEL_ID})")


# ==========================================
# AWS Lambda 진입점 (Handler)
# ==========================================
slack_handler = SlackRequestHandler(app)


def lambda_handler(event, context):
    # EventBridge 예약 이벤트는 "source": "aws.events" 필드를 포함하므로 이를 통해 스케줄 호출을 식별
    if event.get("source") == "aws.events" or event.get("detail-type") == "Scheduled Event":
        post_monthly_reminder(force=event.get("force", False))
        return {"statusCode": 200, "body": "reminder check done"}

    # 그 외의 요청은 API Gateway를 통한 Slack 이벤트/커맨드로 간주하여 Bolt 핸들러로 전달
    return slack_handler.handle(event, context)