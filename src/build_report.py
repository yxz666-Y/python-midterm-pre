from pathlib import Path
import pandas as pd
from docx import Document
from docx.shared import Pt,Inches,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
R=Path(__file__).resolve().parents[1]
d=Document(R/'references/项目报告模版.docx')
# Reuse template package, section, named styles, and cover/body typography.
body=d._element.body
for sec in d.sections:
 grid=sec._sectPr.find(qn('w:docGrid'))
 if grid is not None:sec._sectPr.remove(grid)
 fp=sec.footer.paragraphs[0];fp.alignment=1
 field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');fp._p.append(field)
for e in list(body):
 if e.tag!=qn('w:sectPr'):body.remove(e)
for style in d.styles:
 if style.type==1:
  style.font.name='Arial Unicode MS';style.font.color.rgb=RGBColor(0,0,0)
  style.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Arial Unicode MS')
d.styles['Normal'].font.size=Pt(12)
d.styles['Normal'].paragraph_format.line_spacing=1.35
d.styles['Normal'].paragraph_format.space_after=Pt(7)
for name in ['Heading 1','Heading 2']:d.styles[name].font.size=Pt(14)
def p(t):return d.add_paragraph(t)
def h(t):return d.add_heading(t,1)
def page(t):
 a=h(t);a.paragraph_format.page_break_before=True
def pic(name,caption):d.add_picture(str(R/'figures'/name),width=Inches(4.7 if name=='comparison.png' else 5.8));a=p(caption);a.alignment=1;a.runs[0].font.size=Pt(10)
def table(headers,rows):
 t=d.add_table(rows=1, cols=len(headers))
 borders=OxmlElement('w:tblBorders')
 for side in ['top','left','bottom','right','insideH','insideV']:
  e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
 t._tbl.tblPr.append(borders)
 for c,v in zip(t.rows[0].cells,headers):c.text=str(v)
 for row in rows:
  for c,v in zip(t.add_row().cells,row):c.text=str(v)
 for row in t.rows:
  for c in row.cells:
   for a in c.paragraphs:
    a.paragraph_format.space_after=Pt(4)
    for run in a.runs:run.font.size=Pt(10)
 return t
p('评分：_______')
for text,size in [('《Python数据分析编程》',28),('项目报告',36),('无人设备电池健康评估\n与剩余寿命预测',18)]:
 a=p(text);a.alignment=1;a.paragraph_format.space_before=Pt(30)
 for r in a.runs:r.font.size=Pt(size);r.bold=True
p('\n')
for text in ['学院：待补充','专业：待补充','学号：25121619','学生姓名：杨晓真','课程：Python数据分析编程','小组与其他成员：待补充']:
 a=p(text);a.alignment=1
page('目录')
for t,pg in zip(['摘要与关键词','1 引言','2 数据介绍','3 数据清洗与预处理','4 退化规律与健康状态','5 特征与容量预测模型','6 模型评估与不确定性','6.1 寿命外推与阈值敏感性','7 总结与结论','8 小组成员分工与个人承担','9 附录'],[3,4,5,6,7,8,9,11,12,13,14]):p(f'{t}  ……  {pg}')
p('章节导航按正文顺序排列。封面及成员信息需在提交前补全。')
page('摘要')
p('本项目使用课程提供的四块锂离子电池636条逐循环容量记录，研究容量退化、短期预测与剩余寿命外推。数据无缺失和重复记录，环境温度固定为24℃。分别建立上一循环基线、循环线性回归和历史特征岭回归，采用按电池时间先后划分的训练、验证和测试集。四块电池测试集均以简单基线误差最小，其RMSE为0.0082至0.0273 Ah，说明相邻循环的局部连续性比全局线性趋势更适合本次单步任务。')
p('以首循环容量的80%为研究阈值，另用早期30%记录拟合线性与二次趋势并外推首次达阈循环。线性模型对B0005的达阈预测为229循环，而实测为101循环，反映早期趋势外推的明显风险。验证残差构造的经验区间在B0018岭回归测试中仅覆盖33.3%的观测，提示时间漂移使区间可靠性下降。建议使用滚动容量监测及复测机制，避免仅凭单一外推寿命作出更换决定。结论只适用于本数据及研究阈值，不能直接转化为真实飞行安全或续航保证。')
p('关键词：电池老化；容量预测；岭回归；剩余寿命；时间序列验证')
page('1 引言')
p('电池容量下降影响无人设备的可用能量与任务规划。课程题目要求在数据分析基础上建立健康或寿命预测模型，并明确预测误差及不确定性。本项目关注三个问题：不同电池退化是否一致；历史容量能否帮助下一循环预测；早期趋势能否可靠推断达阈时间。')
p('课程说明指出数据整理自NASA PCoE公开电池老化数据集。本项目实际分析对象为课程CSV，未重新下载或拼接其他版本数据。选择全部四块电池，避免仅展示效果较好的个体。容量用Ah表示，循环次数不是日历时间。CSV中没有内阻、电压、电流和设备负载，因此不能分析内阻增长、热失控或真实任务续航。')
p('报告把两个预测任务分开。短期任务在每次新观测到达后预测下一循环，可使用上一循环真实容量；寿命任务固定在早期预测时点，之后不再读取真实容量，检验趋势外推能力。两者的信息条件不同，不直接比较误差大小来判断模型普遍优劣。')
page('2 数据介绍')
table(['字段','类型与含义'],[['battery_id','电池编号，分类标识'],['cycle','循环编号，整数，无时间单位'],['capacity_Ah','逐循环放电容量，连续数值，Ah'],['ambient_temp_C','环境温度，数值，℃，全为24']])
s=pd.read_csv(R/'results/summary.csv')
table(['电池','记录数','初始容量','末次容量','相对下降'],[[r.battery_id,r.n,f'{r.initial:.4f}',f'{r.last:.4f}',f'{r.loss_pct:.2f}%'] for r in s.itertuples()])
p('数据共636行4列，容量范围为1.1538–2.0353 Ah。B0005、B0006、B0007各有168次循环，B0018有132次。末次记录不是统一的寿命终点。表中下降率按1减去末次容量与首循环容量之比计算，因此各电池参考容量不同。')
page('3 数据清洗与预处理')
p('先读取CSV并校验四个字段，再按电池编号和循环次数排序。检查结果为：四列缺失数均为0，完全重复记录数为0，电池与循环组成的主键无重复，容量全部为正。各电池循环编号从1连续递增，没有缺号。保留全部636条记录，不进行无依据的删除或插值。')
p('循环编号为整数，容量及温度为浮点数，电池编号保留字符串。环境温度恒定，不能为回归提供变化信息，因此不作为预测特征。模型按电池独立训练，不把不同个体拼接成一条时间序列。')
p('相邻容量差分中，四块电池分别出现33、26、47和21次正向变化。正向变化是需解释的局部回升，并不自动等于录入错误。仅凭现有字段不能区分测量波动、恢复效应及试验条件变化，所以保留原始波动，并在误差评估中反映其影响。清洗并不意味着强制曲线单调。')
p('对岭回归输入做训练段均值与标准差标准化，验证段和测试段不参与其拟合。前5次循环用于构造历史窗口，不作为岭回归训练目标。所有用于预测第t循环的容量特征仅来自t之前，避免目标泄漏。')
page('4 退化规律与健康状态')
pic('degradation.png','图1 四块电池的原始容量退化曲线')
p('四块电池总体退化，但下降速率和回升幅度不同。B0006从2.0353降至1.1857 Ah，相对下降41.74%，为四者最大；B0007末次相对下降24.25%，最小。该排序基于各自记录窗口，B0018窗口更短，不能当作相同寿命长度的严格排名。')
p('定义SOH(t)=Q(t)/Q(1)×100%。此处首循环实测值是可获得的参考容量，而非制造商额定容量。研究阈值设为80%，用于统一分析流程，不宣称为本设备的强制报废标准。')
page('5 特征与容量预测模型')
p('每块电池前60%作为训练段，中间20%为验证段，最后20%为测试段，边界取整数下界。168行的电池边界为100和134；132行的电池为79和105。测试样本数分别34、34、34、27。模型在验证后使用前80%重新拟合，再对测试段逐循环预测，参数保持固定。')
table(['方法','输入与估计'],[['上一循环基线','预测值等于上次实测容量，无可调参数'],['循环线性回归','Q=a+b×cycle，最小二乘估计'],['历史特征岭回归','cycle、Q(t−1)、Q(t−2)、前5次均值、前5次端点斜率']])
p('岭回归最小化平方误差之和加α乘系数平方和，截距不惩罚。候选α为0.01、0.1、1、10、100，以验证RMSE最小选取，四块电池依次选到0.01、10、10、0.01。实现使用NumPy矩阵运算与伪逆，便于查看估计过程。')
p('评价使用MAE=mean(|预测−实测|)、RMSE=sqrt(mean((预测−实测)²))及偏差Bias=mean(预测−实测)，单位均为Ah。MAE描述平均绝对偏离，RMSE更强调大误差，负偏差表示低估容量。报告逐电池比较，避免不同样本长度掩盖个体问题。')
page('6 模型评估与不确定性')
m=pd.read_csv(R/'results/metrics.csv')
table(['电池','模型','MAE','RMSE'],[[r.battery_id,r.model,f'{r.MAE:.4f}',f'{r.RMSE:.4f}'] for r in m.itertuples()])
pic('comparison.png','图2 各电池测试段RMSE比较')
p('基线在四块电池上均最优。岭回归虽然优于循环线性回归，但未超过基线。局部容量波动和退化速率改变，使复杂特征组合并不必然改善泛化。这里的最优仅指这一预先设置的时间切分。')
page('6 模型评估与不确定性 续')
pic('predictions.png','图3 测试段预测曲线，虚线表示测试起点')
p('线性回归测试偏差均为负，B0018偏差为−0.0948 Ah。相邻容量基线能紧跟慢变趋势，但突发回升时仍会出现误差。')
p('用验证段绝对残差的90%经验分位数构造预测值±半宽区间，半宽固定用于测试。由于最终重新拟合模型，且序列非独立同分布，该区间只是经验误差带，不具有严格90%覆盖保证。岭回归在B0005、B0006、B0007、B0018上的测试覆盖率为91.2%、97.1%、91.2%、33.3%。最后一个个体表明验证误差可能低估后期风险。')
p('提前预警可在预测区间下界低于研究阈值时触发复测，代价是误报增加；仅按点预测触发可能漏掉快速下降。此策略属于建议，尚未独立评估误报率和漏报率，不能将经验区间当作安全承诺。')
page('6.1 寿命外推与阈值敏感性')
u=pd.read_csv(R/'results/rul.csv')
table(['电池','预测起点','实测首次达阈','线性预测','二次预测'],[[b,int(g.origin.iloc[0]),int(g.observed_crossing.iloc[0]),int(g.predicted_crossing.iloc[0]),int(g.predicted_crossing.iloc[1])] for b,g in u.groupby('battery_id')])
p('固定使用前30%观测拟合线性和二次趋势，对未来循环外推至500次，找首次预测容量不高于80%首循环容量的循环。预测起点分别50、50、50、39，均在真实首次达阈之前。RUL=首次达阈循环−预测起点。未来真实容量只用于离线评价，不参与拟合。')
p('B0005实际RUL为51次，线性预测179次、二次54次。B0007实际74次，线性167次、二次49次。二次模型在B0005达阈时间上更接近，但B0007剩余观测段容量RMSE达到0.2741 Ah，说明达阈时间偶然接近不等于整段轨迹可靠。B0018线性和二次预测分别提前11和19次达阈。')
p('阈值变化会直接改变RUL标签与结论。80%是本报告的研究设定；若采用75%或85%，必须重新计算首达时间。容量回升也可能使曲线短暂跨越后又回到阈值上方。实际运用可要求连续若干次低于阈值并复测，但该规则与本次“首次达阈”定义不同。没有观测到达阈的样本应标记为右删失，不能把记录结束当作失效。')
page('7 总结与结论')
pic('soh.png','图4 相对首循环容量与80%研究阈值')
p('本数据支持的结论是：电池间退化差异显著；上一循环基线在本次单步预测中表现最好；早期寿命外推对趋势形式敏感。四块电池首次达到研究阈值分别为101、61、124、75循环，不能采用一刀切的循环寿命。')
p('建议保留每次容量观测，监控近期下降速度及异常跳变；对B0006这类下降较快的个体更早复核容量。对B0018这类后期误差增大的个体，应重新校准误差带、缩短预测范围。更换安排应综合复测、任务需求及设备规范，本项目不能给出真实飞行续航或安全放行结论。')
p('局限包括仅4个电池、单一温度、无负载及内阻信息、单次时间切分。后续可补充独立电池与多温度数据、采用滚动时间验证，并比较更多预测起点。当前模型只验证已知电池的后续循环，不证明对新电池具有相同精度。')
page('8 小组成员分工与个人承担')
table(['成员','学号','承担章节或模块','具体工作'],[['杨晓真','25121619','待本人确认','待按实际参与填写'],['待补充','待补充','待成员确认','待按实际参与填写'],['待补充','待补充','待成员确认','待按实际参与填写']])
p('个人承担说明需要每位成员依据真实工作补全：负责内容、分析思路、使用方法与步骤、遇到的问题和解决方式。当前已知身份仅为杨晓真，不能代替其他成员确认贡献。')
p('本次代码、分析和文档由AI辅助生成，需由小组运行复核并理解方法。已有提交保留在GitHub；提交作者字段不等于三位成员均已完成相应工作。各成员后续应使用自己的真实身份提交实际修改，不倒填或伪造成员历史。')
p('建议讨论的协作模块为数据与探索、模型与评估、报告与汇报，但这仅为分工建议，不能直接写成已完成的个人承担。')
page('9 附录')
p('代码仓库：https://github.com/yxz666-Y/python-midterm-pre')
p('主要入口：src/analyze.py。输入为data/battery.csv，输出为results内CSV与figures内PNG。运行方式：安装requirements.txt后执行 python src/analyze.py。结果确定性生成，不使用随机打乱。')
p('核心特征与估计代码节选如下，完整实现以仓库为准。')
code='''# 预测目标为 q[i]，特征只能取 i 之前\nx = [cycle[i], q[i-1], q[i-2],\n     q[i-5:i].mean(), (q[i-1]-q[i-5])/4]\n# 标准化参数只由训练输入计算\nz = np.column_stack([np.ones(len(x)), (x-mu)/sd])\npen = np.eye(z.shape[1])*alpha\npen[0, 0] = 0\nw = np.linalg.pinv(z.T@z + pen) @ z.T @ y'''
a=p(code)
for r in a.runs:r.font.size=Pt(9)
p('资料依据：课程题目三说明、课程报告与汇报要求、项目报告模版、题3_电池健康老化.csv。数据的NASA来源为课程文件所述，本文未对NASA原始试验元数据做额外核验。')
p('提交前补全：学院、专业、组号、组长、另外两位成员及真实分工。PPT与MP4须更名为“组号_3_组长姓名”，按课程安排提交。视频配音为合成语音演示版本，小组应核验是否符合教师录制要求。')
d.save(R/'deliverables/题目三_项目报告.docx')
print('report saved')
