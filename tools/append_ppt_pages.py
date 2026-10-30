"""在过程PPT末尾追加第九步的不确定性评估与维护建议页面。

只读取既有结果，不重新训练模型；重复运行时会因已存在同名主题页而停止。
用法：python tools/append_ppt_pages.py [--out 交付文件名]
"""
from pathlib import Path
import argparse
import struct

from pptx import Presentation
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
PPT = ROOT / 'deliverables' / '题目三_工作过程.pptx'
FIG = ROOT / 'figures' / 'step09'
FONT = 'Arial Unicode MS'

TITLE_BOX = (Inches(0.62), Inches(0.42), Inches(12.08), Inches(0.89))
FOOTER_BOX = (Inches(0.62), Inches(6.93), Inches(11.46), Inches(0.31))
PAGE_BOX = (Inches(12.19), Inches(6.93), Inches(0.78), Inches(0.31))
IMAGE_BOX = (Inches(0.68), Inches(1.45), Inches(11.77), Inches(4.15))
CAPTION_BOX = (Inches(0.68), Inches(5.72), Inches(11.77), Inches(1.05))
BODY_BOX = (Inches(0.68), Inches(1.55), Inches(11.77), Inches(5.10))
FOOTER_TEXT = '工作过程记录  杨晓真 25121619  2026.10.28'

PAGES = [
    {'title': '06 / 误差方向与容量高估风险',
     'image': '01_error_risk.png',
     'caption': ['平均偏差（预测−实测）：回归 −0.0111 Ah、森林 +0.0444 Ah、基线 +0.0023 Ah。',
                 '森林在B0005、B0006、B0007的全部34个测试点上高估容量，B0006最大高估0.173 Ah。',
                 '高估比低估更危险；不能因为回归整体偏低估就断言它更安全。']},
    {'title': '06 / 提前预警与寿命外推的不确定性',
     'image': '03_lifetime_sensitivity.png',
     'caption': ['四块电池首次跌到80%研究阈值的循环为101、61、124、75，均早于测试起点135（B0018为106），单步预测无法验证提前预警。',
                 '241个滚动起点只对应4个真实事件：最近20次线性趋势检出3次，容量保持基线全部漏报。',
                 '仅用前30%与50%历史外推时B0005估到228.6、115.1次（实测101）；历史变长不保证更准，该范围不是置信区间。']},
    {'title': '07 / 使用、维护与更换建议',
     'body': ['· 保留容量保持作参照基线：它不训练任何参数，平均误差最低，可作为判断其他模型的下限。',
              '· 逐电池查看预测偏差与最大高估，不能只看平均RMSE；本次森林后期持续高估，不能据此乐观安排续航。',
              '· 接近研究阈值（首循环容量的80%）时用新一轮实测复核再决策，不要凭早期线性交点确定更换日期。',
              '· 不要把容量误差换算成飞行分钟数或剩余寿命；数据集缺少任务能耗、电流与内阻信息。',
              '· 需要新电池与更多工况外部验证后才可推广；结论只适用于这四块电池、24℃与本次时间划分。']},
]


def png_size(path):
    """从PNG文件头读取像素尺寸，用于保持插入图片的长宽比。"""
    head = Path(path).read_bytes()[:26]
    width, height = struct.unpack('>II', head[16:24])
    return width, height


def style_run(run, size_pt, name=FONT, bold=False):
    """同时设置西文与东亚字体，避免中文回退到默认字体。"""
    run.font.size = Pt(size_pt)
    run.font.name = name
    run.font.bold = bold
    properties = run.font._rPr
    element = properties.find(qn('a:ea'))
    if element is None:
        element = parse_xml(f'<a:ea {nsdecls("a")} typeface="{name}"/>')
        properties.insert_element_before(element, 'a:cs', 'a:sym', 'a:hlinkClick',
                                         'a:hlinkMouseOver', 'a:rtl', 'a:extLst')
    else:
        element.set('typeface', name)


def add_text(slide, lines, box, size_pt, bold=False):
    """按行写入一个文本框，每行一个段落。"""
    textbox = slide.shapes.add_textbox(*box)
    frame = textbox.text_frame
    frame.word_wrap = True
    for index, line in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        run = paragraph.add_run()
        run.text = line
        style_run(run, size_pt, bold=bold)
    return textbox


def add_scaled_picture(slide, image, box):
    """按原图长宽比放入给定区域，避免图片被拉伸。"""
    left, top, max_width, max_height = box
    width, height = png_size(image)
    scale = min(max_width / width, max_height / height)
    return slide.shapes.add_picture(str(image), left, top,
                                    int(width * scale), int(height * scale))


def append_page(prs, spec, page_number):
    """新建空白页并写入标题、正文（图＋图注或要点）、页脚与页码。"""
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    for placeholder in list(slide.shapes):
        if placeholder.is_placeholder:
            placeholder._element.getparent().remove(placeholder._element)
    add_text(slide, [spec['title']], TITLE_BOX, 29.25)
    if 'image' in spec:
        add_scaled_picture(slide, FIG / spec['image'], IMAGE_BOX)
        add_text(slide, spec['caption'], CAPTION_BOX, 16.0)
    else:
        add_text(slide, spec['body'], BODY_BOX, 20.0)
    add_text(slide, [FOOTER_TEXT], FOOTER_BOX, 12.0)
    add_text(slide, [str(page_number)], PAGE_BOX, 12.0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default=str(PPT), help='输出文件，默认覆盖原PPT')
    args = parser.parse_args()

    prs = Presentation(str(PPT))
    existing = {shape.text_frame.text
                for slide in prs.slides for shape in slide.shapes
                if shape.has_text_frame}
    todo = [spec for spec in PAGES if spec['title'] not in existing]
    if not todo:
        raise SystemExit('这三页已存在，未重复追加。')

    first_page = len(prs.slides) + 1
    for offset, spec in enumerate(todo):
        append_page(prs, spec, first_page + offset)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    print(f'原 {len(existing)} 个文本框；追加 {len(todo)} 页；总页数 {len(prs.slides)}；保存于 {out}')


if __name__ == '__main__':
    main()
