"""macOS say 合成配音演示稿；各页持续时间合计300秒。"""
from pathlib import Path
import subprocess,json,wave
import imageio_ffmpeg
R=Path(__file__).resolve().parents[1];tmp=R/'.build/video';tmp.mkdir(exist_ok=True)
ff=imageio_ffmpeg.get_ffmpeg_exe();slides=json.loads((R/'results/slides.json').read_text())
script=['# 五分钟汇报讲稿','配音演示版使用macOS Tingting合成语音，并非杨晓真本人录音。组长与组号确认后按要求改名。']
for i,(title,body,duration,speech) in enumerate(slides,1):
 script += [f'## 第{i}页 {duration}秒',speech]
 txt=tmp/f'{i}.txt';txt.write_text(speech)
 subprocess.run(['say','-v','Tingting','-r','210','-f',str(txt),'-o',str(tmp/f'{i}.aiff')],check=True)
 subprocess.run([ff,'-y','-i',str(tmp/f'{i}.aiff'),str(tmp/f'{i}.wav')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 with wave.open(str(tmp/f'{i}.wav')) as w:actual=w.getnframes()/w.getframerate()
 rate=max(.5,actual/(duration-1))
 subprocess.run([ff,'-y','-loop','1','-i',str(R/f'.build/slides/slide-{i}.png'),'-i',str(tmp/f'{i}.wav'),'-af',f'atempo={rate:.6f},apad','-t',str(duration),'-r','24','-c:v','libx264','-preset','fast','-tune','stillimage','-pix_fmt','yuv420p','-c:a','aac','-ar','48000',str(tmp/f'{i}.mp4')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 print('video segment',i,flush=True)
(tmp/'list.txt').write_text('\n'.join(f"file '{i}.mp4'" for i in range(1,len(slides)+1)))
subprocess.run([ff,'-y','-f','concat','-safe','0','-i',str(tmp/'list.txt'),'-c','copy',str(R/'deliverables/待填组号_3_待确认组长.mp4')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
(R/'deliverables/五分钟汇报讲稿.md').write_text('\n\n'.join(script))
