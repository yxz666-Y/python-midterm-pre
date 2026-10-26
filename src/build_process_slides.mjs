// 当前工作过程PPT：先运行01、02，再使用Codex的artifact-tool依赖运行此脚本。
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
const req=createRequire(process.env.RUNTIME_NODE_MODULES+'/package.json');
const {Presentation,PresentationFile}=await import(req.resolve('@oai/artifact-tool'));
const skill=process.env.PRESENTATIONS_SKILL || '/Users/yangxiaozhen/.codex/plugins/cache/openai-primary-runtime/presentations/26.1024.11018/skills/presentations';
const {finalizePresentation,applyPresentationChartFont}=await import(skill+'/container_tools/artifact_tool_utils.mjs');
const root=process.cwd(), out=root+'/.build/process';
await fs.mkdir(out,{recursive:true});
const d=JSON.parse(await fs.readFile('results/step02/slides_data.json','utf8'));
const p=Presentation.create({slideSize:{width:1280,height:720}});
const colors=['#176B87','#D3662E','#647D32','#8A4E9C'];
function text(s,t,x,y,w,h,size=28,color='#172B3A'){const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});a.text=t;a.text.style={fontFamily:'Arial Unicode MS',fontSize:size,color};return a;}
function slide(title,notes){let s=p.slides.add();s.background.fill='#FFFFFF';text(s,title,60,40,1160,90,39);text(s,'工作过程记录  |  杨晓真 25121619  |  2026.10.26',60,665,1100,30,16,'#687985');text(s,String(p.slides.items.length),1170,665,75,30,16);s.speakerNotes.text=notes+'\n数据来源：课程题目三 data/battery.csv；代码 src/01_read_and_clean.py、src/02_visualize_degradation.py；统计 results/step01、results/step02。';return s;}
function chart(s,ids,key,n,pos){const c=s.charts.add('line',{position:pos,categories:Array.from({length:n},(_,i)=>String(i+1)),series:ids.map(id=>({name:id,values:d.batteries[id][key].slice(0,n),fill:colors[Object.keys(d.batteries).indexOf(id)]})),hasLegend:true,xAxis:{title:'循环次数'},yAxis:{title:key==='capacity'?'容量（Ah）':'相对首循环容量（%）'}});applyPresentationChartFont(c,{fontFamily:'Arial Unicode MS'});}
let s=slide('电池容量退化：从读入数据到识别差异','这是重新开始的工作过程记录，仅记录已经完成的读取、清洗与可视化。后续模型比较和不确定性分析将在下一阶段补充，不把旧成果当作当前学习过程。');
text(s,'题目三  无人设备电池健康评估与剩余寿命预测',65,175,1140,70,32);
text(s,'01  读取与清洗：检查数据能否用于分析\n\n02  可视化退化：观察趋势并比较个体差异\n\n本阶段成果：两份Python代码、三张图、对比表',65,285,1130,320,31);
s=slide('01 / 数据读取：一行代表一次放电循环','使用pandas.read_csv读取UTF-8编码CSV。先检查前几行、形状和数据类型，而不是直接建模。电池编号是个体标识，循环次数是时间顺序，容量是目标变量，温度是条件字段。');
text(s,'pd.read_csv(..., encoding="utf-8-sig")\ndf.head()    df.shape    df.dtypes',65,160,1130,115,31,'#176B87');
text(s,'636行 × 4列；4块电池；环境温度均为24℃\n\nbattery_id：电池编号      cycle：放电循环次数\ncapacity_Ah：放电容量   ambient_temp_C：环境温度\n\nB0005 / B0006 / B0007 各168次；B0018 为132次',65,315,1140,300,28);
s=slide('01 / 清洗：先验证，再决定是否处理','检查结果：无缺失、无完全重复行、无电池编号与循环次数冲突、循环从1开始连续；容量为正且数值有限。原始数据无需删点，清洗后仍为636行。不能仅因容量局部回升就判断数据错误。');
text(s,'字段规范 → 数值转换 → 缺失与重复检查\n\n有效数值与正容量 → 循环连续性 → 分组排序',65,165,1140,150,32,'#176B87');
text(s,'实测检查：缺失0；重复0；主键冲突0；循环缺口0\n\n清洗前636行 → 清洗后636行；容量范围1.1538–2.0353 Ah\n\n输出 battery_clean.csv 与 battery_summary.csv\n保留原始CSV；不插值、不平滑、不删除局部回升',65,365,1140,250,27);
s=slide('02 / 画图前：明确两种比较口径','第一种图保留所有观测，说明完整记录中的退化趋势。第二种限制在所有电池共有的前132次，并用各自首循环容量归一化；避免观察长度与初始容量造成混淆。相对首循环容量不是制造商额定容量口径的SOH。');
text(s,'完整容量曲线：横轴循环次数，纵轴容量Ah\n逐块电池 groupby 后 plt.plot，B0018在132次处结束',65,170,1140,130,29);
text(s,'共同窗口：第1—132次循环\n相对容量 = 当前容量 ÷ 本电池首循环容量 × 100%\n下降比例 = (1 − 第132次容量 ÷ 首循环容量) × 100%',65,345,1140,200,30,'#176B87');
text(s,'目的：区分“初始容量大小”和“相对退化程度”。',65,580,1140,50,27);
s=slide('实际容量曲线：前三块电池的全部168次记录','前三块电池都有168次观测。B0006起始容量最高，但后期容量低于另外两块。线条总体下降但有局部回升。第四块电池记录较短，下一页单独展示完整记录。');
chart(s,['B0005','B0006','B0007'],'capacity',168,{left:65,top:150,width:1130,height:435});
text(s,'初始容量高，不代表后期仍保持较高容量；局部回升并未被抹去。',65,605,1140,45,26);
s=slide('B0018：观测到132次，之后没有数据','B0018首循环1.8550Ah，第132次为1.3411Ah。记录终止不能解释为电池失效，也不能给它补出后续容量。完整四电池叠加图保存在figures/step02/01_capacity_all_cycles.png。');
chart(s,['B0018'],'capacity',132,{left:65,top:150,width:1130,height:435});
text(s,'1.8550 Ah → 1.3411 Ah；观测结束不等于失效，后续状态未知。',65,605,1140,45,26);
s=slide('统一前132次后，B0006退化最多，B0007最少','四条曲线均以各自第1次容量为100%。第132次的下降比例：B0005为26.49%，B0006为35.36%，B0007为21.90%，B0018为27.70%。这是这四块电池的描述性结果，不代表总体显著性检验或寿命排名。');
chart(s,Object.keys(d.batteries),'retention',132,{left:65,top:150,width:1130,height:435});
text(s,'首循环统一为100%；同一观察长度下比较相对退化程度。',65,605,1140,45,26);
s=slide('差异量化：同样经历131个循环间隔','从第1次到第132次有131个相邻间隔。最大与最小容量下降比例差13.46个百分点。B0005和B0018的下降比例接近，但不能因此推断它们后续寿命相同。');
const c=s.charts.add('bar',{position:{left:65,top:160,width:760,height:430},categories:d.summary.map(r=>r.battery_id),series:[{name:'下降比例（%）',values:d.summary.map(r=>r.loss_pct),fill:'#176B87'}],barOptions:{direction:'column',grouping:'clustered'},hasLegend:false,yAxis:{title:'下降比例（%）'}});applyPresentationChartFont(c,{fontFamily:'Arial Unicode MS'});
text(s,d.summary.map(r=>`${r.battery_id}  ${r.loss_pct.toFixed(2)}%`).join('\n\n'),870,205,345,300,29);
text(s,'B0006比B0007多下降13.46个百分点；这是观测差异，不是因果解释。',65,605,1140,45,25);
s=slide('局部回升值得保留，但不能据此解释原因','同一前132次窗口，共131个相邻间隔，容量增加的间隔数依次为22、18、34、21。回升次数多不等于回升幅度大，也不等于电池更健康。本阶段不区分测量误差或恢复效应，现有数据不足以归因。');
text(s,'前132次中的回升间隔数（每块均有131个间隔）',65,170,1140,55,31);
text(s,d.summary.map(r=>`${r.battery_id}：${r.rebound_count}次`).join('        '),65,285,1140,70,30,'#176B87');
text(s,'整体退化与短期波动同时存在\n\n回升次数 ≠ 回升幅度，也不能单独作为健康排名\n\n缺少内阻、电流、负载等字段，不能断言差异的物理原因',65,400,1140,210,29);
s=slide('本阶段结论与下一步','当前完成读取清洗和探索性可视化。未来步骤还需至少两种预测方法、按时间划分评估、预测误差和提前预警与寿命外推的不确定性讨论。本页是计划，不是完成声明。用户要求不制作视频。Git保留旧版本，当前移除旧报告与PPT，建立这份过程稿。');
text(s,'已完成：数据检查、全部退化曲线、共同窗口差异比较\n\n发现：B0006下降最多，B0007最少；局部回升不可忽略\n\n边界：仅4块电池、24℃；不能直接推广到实际飞行续航\n\n下一步：提取历史特征 → 比较至少两种模型 → 评估不确定性',65,165,1140,340,29);
text(s,'复现：01_read_and_clean.py → 02_visualize_degradation.py\nGitHub：yxz666-Y/python-midterm-pre',65,550,1140,85,24,'#176B87');
for(const [i,s] of p.slides.items.entries()){const blob=await p.export({slide:s,format:'png',scale:1});await fs.writeFile(`${out}/slide-${i+1}.png`,new Uint8Array(await blob.arrayBuffer()));}
await (await PresentationFile.exportPptx(p)).save(out+'/candidate.pptx');
await finalizePresentation({workspaceDir:root,candidatePath:out+'/candidate.pptx',finalPath:root+'/deliverables/题目三_工作过程_读取清洗与退化分析.pptx',pythonExecutable:'/Users/yangxiaozhen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000'],requiredNativeChartOwnerSlides:[5,6,7,8],materializeLiteralChartWorkbooks:true,verifyArtifactToolImport:true,receiptPath:out+'/validation-'+Date.now()+'.json'});
