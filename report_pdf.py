"""
'월간 현황 보고서' 양식을 채워서 PDF로 직접 생성하는 모듈 (reportlab 사용).

Word/LibreOffice 없이 순수 파이썬으로 PDF를 만들기 때문에, 사용자 컴퓨터에
별도 오피스 프로그램이 없어도 동작함 (단, 한글 폰트 파일이 필요)

한글 폰트 경로:
  Windows 기본 설치본에는 맑은 고딕(malgun.ttf / malgunbd.ttf)이 C:\\Windows\\Fonts 에 이미 들어있어서 별도 설치가 필요 없는 경우가 많음
  못 찾으면 KOREAN_FONT_REGULAR / KOREAN_FONT_BOLD 환경변수로 경로를 직접 지정 필요
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

# 폰트 경로 설정
FONT_REGULAR_CANDIDATES = [
    os.environ.get("KOREAN_FONT_REGULAR", ""),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "NanumGothic.ttf"),  # 번들 폰트 (Lambda용)
    r"C:\Windows\Fonts\malgun.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
]
FONT_BOLD_CANDIDATES = [
    os.environ.get("KOREAN_FONT_BOLD", ""),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "NanumGothicBold.ttf"),  # 번들 폰트 (Lambda용)
    r"C:\Windows\Fonts\malgunbd.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
]

_FONT_REGISTERED = False

# 폰트 유무 체크
def _register_fonts():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return

    reg_path = next((p for p in FONT_REGULAR_CANDIDATES if p and os.path.exists(p)), None)
    bold_path = next((p for p in FONT_BOLD_CANDIDATES if p and os.path.exists(p)), None)

    if not reg_path:
        raise FileNotFoundError(
            "한글 폰트를 찾을 수 없습니다. Windows라면 보통 C:\\Windows\\Fonts\\malgun.ttf 가 있어야 하는데 "
            "없다면 KOREAN_FONT_REGULAR 환경변수로 다른 한글 TTF 폰트 경로를 지정해주세요."
        )
    if not bold_path:
        bold_path = reg_path  # 볼드 폰트 없으면 일반 폰트로 대체

    pdfmetrics.registerFont(TTFont("Korean", reg_path))
    pdfmetrics.registerFont(TTFont("Korean-Bold", bold_path))
    _FONT_REGISTERED = True

# pdf 문서 생성
def generate_report_pdf(
    output_path,
    year,
    month,
    author,
    plan_this_month,
    result_this_month,
    plan_next_month,
    remark,
    issues,
    requests_text,
):
    _register_fonts()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    title_style = ParagraphStyle(
        "Title", fontName="Korean-Bold", fontSize=20, alignment=TA_CENTER, spaceAfter=6
    )
    author_style = ParagraphStyle(
        "Author", fontName="Korean", fontSize=11, alignment=TA_RIGHT, spaceAfter=14
    )
    header_style = ParagraphStyle(
        "CellHeader", fontName="Korean-Bold", fontSize=10, alignment=TA_CENTER
    )
    body_style = ParagraphStyle(
        "CellBody", fontName="Korean", fontSize=9.5, leading=13
    )

    def p(text, style):
        # Paragraph는 \n을 인식 못하므로 <br/>로 변환
        safe = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = safe.replace("\n", "<br/>")
        return Paragraph(safe, style)

    elements = []
    elements.append(p(f"월간 현황 보고서({year}년 {month}월)", title_style))
    elements.append(p(f"작성자 : {author}", author_style))

    HEADER_FILL = colors.HexColor("#E2EFDA")
    col_w = 4.4 * cm

    # ---- 표 1 ----
    table1_data = [
        [p("금월 계획 및 실적", header_style), "", p("차월 계획", header_style), ""],
        [p("계 획", header_style), p("실 적", header_style), p("계 획", header_style), p("비 고", header_style)],
        [p(plan_this_month, body_style), p(result_this_month, body_style), p(plan_next_month, body_style), p(remark, body_style)],
    ]
    table1 = Table(table1_data, colWidths=[col_w] * 4)
    table1.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (1, 0)),
                ("SPAN", (2, 0), (3, 0)),
                ("BACKGROUND", (0, 0), (-1, 1), HEADER_FILL),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(table1)
    elements.append(Spacer(1, 0.6 * cm))

    # ---- 표 2 ----
    table2_data = [
        [p("애로 사항", header_style)],
        [p(issues, body_style)],
        [p("요청 및 전달 사항", header_style)],
        [p(requests_text, body_style)],
    ]
    table2 = Table(table2_data, colWidths=[col_w * 4])
    table2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), HEADER_FILL),
                ("BACKGROUND", (0, 2), (0, 2), HEADER_FILL),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(table2)

    doc.build(elements)
    return output_path


if __name__ == "__main__":
    generate_report_pdf(
        "test_report.pdf",
        year=2026,
        month=8,
        author="홍길동",
        plan_this_month="[업무]\n1. 테스트 프로젝트\n- 항목 1\n- 항목 2",
        result_this_month="[업무]\n1. 테스트 프로젝트\n- 완료된 항목 1",
        plan_next_month="[업무]\n1. 다음달 계획 항목",
        remark="",
        issues="특이사항 없음",
        requests_text="없음",
    )
    print("test_report.pdf 생성 완료")