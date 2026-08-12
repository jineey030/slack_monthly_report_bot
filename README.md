# 🤖 월간 현황 보고서 Slack Bot (AWS Lambda 버전)

Slack과 AWS Lambda, 그리고 Dooray! Mail을 연동하여 매월 정기적인 월간 보고서 작성과 PDF 생성을 자동화해 주는 스마트한 서버리스 봇입니다.

## ✨ 주요 기능

- 📅 **정기 알림 자동화 (EventBridge)**: 매월 마지막 주 수요일을 자동으로 계산하여 지정된 Slack 채널에 보고서 작성 독려 알림과 버튼을 전송합니다.
- 📝 **슬래시 커맨드 및 모달 UI**: `/monthly_report` 커맨드나 알림 버튼을 통해 직관적인 모달 팝업 창을 띄워 보고서 정보를 입력받습니다.
- 📄 **자동 PDF 생성 및 전송**: 입력된 데이터를 기반으로 깔끔한 양식의 월간 보고서 PDF를 즉시 생성하여 사용자 개인 DM으로 안전하게 전달합니다.
- 🔗 **두레이(Dooray!) 메일 딥링크 연동**: 수신자, 참조자, 제목이 자동으로 채워진 두레이 메일 작성창을 원클릭으로 열 수 있습니다.

## ⚙️ 시스템 아키텍처 및 동작 방식

이 봇은 두 가지 독립적인 트리거 경로를 하나의 AWS Lambda 함수에서 효율적으로 분기하여 처리합니다.

```text
[AWS EventBridge] ──(Scheduled Event)──┐
├──> [ AWS Lambda (Handler) ]
[Slack API Gateway] ──(HTTP Request)───┘
```

### 🚀 [경로 A] AWS EventBridge 정기 호출 (알림 자동화)

매월 지정된 주기(예: 아침 9시 10분)에 AWS EventBridge가 Lambda를 깨워 정기 업무를 수행합니다.

1. **스케줄 발생**: EventBridge에서 예약된 이벤트(`source: "aws.events"`)를 Lambda로 전달합니다.
2. **트리거 판별**: Lambda 진입점(`lambda_handler`)에서 이벤트 소스를 확인하여 스케줄 호출로 인식합니다.
3. **날짜 조건 검사** (`_is_last_wednesday`): 타임존(`Asia/Seoul`) 기준 오늘 날짜가 해당 월의 마지막 주 수요일이 맞는지 정밀하게 계산합니다.
4. **알림 전송**: 조건에 부합할 경우, 설정된 채널(`REMINDER_CHANNEL_ID`)로 "월간보고 작성하기" 버튼이 포함된 메시지를 발송합니다.

### 💬 [경로 B] 사용자 상호작용 및 슬래시 커맨드 (보고서 생성)

사용자가 직접 봇과 상호작용하여 보고서를 작성하고 발송하는 대화형 경로입니다.

1. **사용자 요청**: 사용자가 Slack 채널에 `/monthly_report` 커맨드를 입력하거나 알림 메시지의 [월간보고 작성하기] 버튼을 클릭합니다.
2. **API Gateway 연동**: Slack 서버가 AWS API Gateway를 거쳐 Lambda 함수로 HTTP 요청을 보냅니다.
3. **모달 창 오픈**: Slack Bolt 프레임워크(`slack_handler`)가 요청을 받아 사용자 화면에 월간 현황 보고서 입력 모달을 띄웁니다.
4. **보고서 제출 및 처리** (`monthly_report_submit`):
   - 사용자가 모달 창에 내용(계획, 실적, 수신자 등)을 입력하고 [생성 및 전송]을 누릅니다.
   - 봇이 즉시 PDF 보고서 파일을 생성합니다.
   - 사용자의 개인 DM 채널로 PDF 파일을 업로드하고, 두레이 메일 작성창 딥링크 버튼을 함께 전송합니다. (제목/수신자/참조자 자동 입력)

## 🛠️ 기술 스택

- **Language**: Python 3.12
- **Framework**: Slack Bolt for Python (`slack_bolt`)
- **Serverless**: AWS Lambda, Amazon API Gateway, Amazon EventBridge
- **Integration**: Dooray! Mail Link

## 📦 의존성 (Dependencies)

| 패키지 | 버전 | 용도 |
|---|---|---|
| `slack-bolt` | 1.18.0 | Slack 이벤트/커맨드/모달 처리 프레임워크 |
| `APScheduler` | 3.10.0 | 스케줄링 관련 작업 처리 |
| `python-docx` | 1.1.0 | Word 문서 생성/처리 |
| `reportlab` | 4.0.0 | PDF 보고서 생성 |

설치는 아래 명령어로 진행합니다.

```bash
pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.12 --only-binary=:all: -r requirements.txt
```

- **Framework**: Slack Bolt for Python (`slack_bolt`)
- **Serverless**: AWS Lambda, Amazon API Gateway, Amazon EventBridge
- **Integration**: Dooray! Mail Link

## 📖 관련 글

이 프로젝트의 개발 과정과 상세한 구현 내용은 아래 블로그 글에 정리되어 있습니다.

- [AWS Lambda + Slack Bot 만들기](https://velog.io/@jineey/AWS-Lambda-Slack-Bot-%EB%A7%8C%EB%93%A4%EA%B8%B0#%EC%86%8C%EC%8A%A4-%EC%BD%94%EB%93%9C-%EC%9E%91%EC%84%B1)
