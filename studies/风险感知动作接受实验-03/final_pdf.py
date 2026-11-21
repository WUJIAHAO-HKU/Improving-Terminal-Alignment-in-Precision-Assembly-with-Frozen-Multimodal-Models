"""Append a typeset independent validation section to the prior experiment PDF."""
from pathlib import Path
from xml.sax.saxutils import escape
from tempfile import TemporaryDirectory
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph,Spacer,Image,SimpleDocTemplate,PageBreak
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
import pymupdf

root=Path(__file__).resolve().parent
old=root.parent/'独立测量策略实验-02/output/pdf/独立测量策略实验报告.pdf'
out=root/'output/pdf/装配测量与动作接受实验合订本.pdf'
out.parent.mkdir(exist_ok=True,parents=True)
pdfmetrics.registerFont(TTFont('YaHei','msyh.ttc',subfontIndex=0))
def style(size,leading,after,color):
    return ParagraphStyle(str(size),fontName='YaHei',fontSize=size,leading=leading,spaceAfter=after,textColor=colors.HexColor(color),wordWrap='CJK')
styles=[style(9.2,15,7,'#253536'),style(14,19,8,'#184e50'),style(20,27,10,'#184e50')]
story=[]
def add(text,i=0):
    story.append(Paragraph(escape(text.strip().replace('**','')),styles[i]))
def image(name,w,h):
    f=root/name
    wi,he=ImageReader(str(f)).getSize();scale=min(w*mm/wi,h*mm/he)
    story.append(Image(str(f),wi*scale,he*scale))
    story.append(Spacer(1,3*mm))
body=(root/'实验报告.md').read_text(encoding='utf8').split('## ')
first,*sections=body
first=first.splitlines()
add(first[0].lstrip('# '),2)
for line in first[1:]:
    if line.strip():add(line)
lines=sections[0].strip().splitlines()
for line in lines:
    if not line:continue
    if line.startswith('!'):continue
    add(line,1 if line==lines[0] else 0)
image('budget-frontier.png',145,76)
story.append(PageBreak())
lines=sections[1].strip().splitlines()
for line in lines:
    if not line:continue
    if line.startswith('!'):
        image('failure-cases.jpg',174,114)
    else:add(line.removeprefix('- '),1 if line==lines[0] else 0)
story.append(PageBreak())
for line in sections[2].strip().splitlines():
    if line.strip():add(line,1 if line.startswith('实验与') else 0)
def footer(c,d):
    c.setFont('YaHei',8);c.setFillColor(colors.HexColor('#596e70'));c.drawString(18*mm,11*mm,'通用模型装配诊断　|　独立实验 03');c.drawRightString(192*mm,11*mm,str(5+d.page))
with TemporaryDirectory() as td:
    appendix=Path(td)/'appendix.pdf'
    doc=SimpleDocTemplate(str(appendix),pagesize=A4,topMargin=15*mm,bottomMargin=18*mm,leftMargin=18*mm,rightMargin=18*mm)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    with pymupdf.open(old) as base,pymupdf.open(appendix) as extra:
        n=len(base);base.insert_pdf(extra);base.set_toc([[1,'实验 02　测量预算',1],[2,'预算曲线',2],[2,'非劣检验',3],[2,'失败案例',4],[2,'下一轮方案',5],[1,'实验 03　独立验证',n+1]])
        base.set_metadata({'title':'装配测量与动作接受｜两轮独立实验','subject':'预算、动作门控、非劣检验与失败回放'})
        base.save(out,deflate=True)
