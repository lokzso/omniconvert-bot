from __future__ import annotations
import asyncio, shutil, zipfile, tarfile, re
from pathlib import Path
from PIL import Image, ImageSequence

IMAGE={'.jpg','.jpeg','.png','.webp','.bmp','.tiff','.tif','.heic','.heif','.gif'}
VIDEO={'.mp4','.mkv','.mov','.avi','.webm','.m4v','.mpeg','.mpg','.3gp'}
AUDIO={'.mp3','.wav','.flac','.aac','.m4a','.ogg','.opus','.wma'}
DOC={'.doc','.docx','.odt','.rtf','.txt','.html','.htm','.ppt','.pptx','.odp','.xls','.xlsx','.ods','.csv'}
ARCHIVE={'.zip','.7z','.tar','.gz','.tgz','.bz2','.xz'}
TARGETS={
'image':['jpg','png','webp','bmp','tiff','pdf'],
'video':['mp4','mkv','webm','mov','gif','mp3','wav','opus'],
'audio':['mp3','wav','flac','m4a','ogg','opus'],
'document':['pdf','docx','odt','txt','html','xlsx','csv','pptx'],
'pdf':['png','jpg','txt'],
'archive':['zip','7z','tar','tar.gz']}

def kind(p:Path):
 e=p.suffix.lower(); n=p.name.lower()
 if e=='.pdf': return 'pdf'
 if e in IMAGE:return 'image'
 if e in VIDEO:return 'video'
 if e in AUDIO:return 'audio'
 if e in DOC:return 'document'
 if e in ARCHIVE or n.endswith('.tar.gz'):return 'archive'
 return 'unknown'

async def run(*args):
 p=await asyncio.create_subprocess_exec(*map(str,args),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
 out,err=await p.communicate()
 if p.returncode: raise RuntimeError(err.decode(errors='ignore')[-2500:])
 return out

def safe_name(name): return re.sub(r'[^\w.() -]+','_',name,flags=re.UNICODE)[:180]

async def convert(src:Path,ext:str,outdir:Path,quality=85,resolution='original',bitrate='auto'):
 ext=ext.lower().lstrip('.'); k=kind(src); outdir.mkdir(parents=True,exist_ok=True)
 dst=outdir/(src.stem+'.'+ext)
 if k=='image':
  if src.suffix.lower() in {'.heic','.heif'}:
   from pillow_heif import register_heif_opener; register_heif_opener()
  im=Image.open(src)
  if ext=='pdf':
   frames=[x.convert('RGB') for x in ImageSequence.Iterator(im)]
   frames[0].save(dst,'PDF',save_all=True,append_images=frames[1:]); return dst
  if ext in ('jpg','jpeg') and im.mode not in ('RGB','L'): im=im.convert('RGB')
  kwargs={'quality':quality} if ext in ('jpg','jpeg','webp') else {}
  im.save(dst,**kwargs); return dst
 if k in ('video','audio'):
  args=['ffmpeg','-y','-i',src]
  if k=='video' and ext not in ('mp3','wav','opus'):
   if resolution!='original': args += ['-vf',f'scale=-2:{resolution}']
   if ext=='gif': args += ['-vf',(f'scale=-2:{resolution},' if resolution!='original' else '')+'fps=15']
   elif bitrate!='auto': args += ['-b:v',bitrate]
  if ext in ('mp3','m4a','ogg','opus','aac') and bitrate!='auto': args += ['-b:a',bitrate]
  args += [dst]; await run(*args); return dst
 if k=='document':
  await run('libreoffice','--headless','--convert-to',ext,'--outdir',outdir,src)
  exact=[p for p in outdir.glob(src.stem+'.*') if p.suffix.lower()=='.'+ext]
  if not exact: raise RuntimeError('LibreOffice не смог сделать этот формат')
  return exact[0]
 if k=='pdf' and ext in ('png','jpg'):
  prefix=outdir/src.stem; await run('pdftoppm','-'+('png' if ext=='png' else 'jpeg'),'-r','180',src,prefix)
  files=sorted(outdir.glob(src.stem+'-*'))
  if len(files)==1:return files[0]
  z=outdir/(src.stem+'_pages.zip')
  with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as f:
   for p in files:f.write(p,p.name)
  return z
 if k=='pdf' and ext=='txt': await run('pdftotext',src,dst); return dst
 if k=='archive':
  unpack=outdir/'unpacked'; unpack.mkdir(exist_ok=True)
  await run('7z','x',src,f'-o{unpack}','-y')
  if ext=='zip':
   z=outdir/(src.stem+'.zip'); shutil.make_archive(str(z.with_suffix('')),'zip',unpack); return z
  if ext=='7z':
   z=outdir/(src.stem+'.7z'); await run('7z','a',z,unpack/'*'); return z
  if ext=='tar':
   z=outdir/(src.stem+'.tar'); shutil.make_archive(str(z.with_suffix('')),'tar',unpack); return z
  if ext=='tar.gz':
   z=outdir/(src.stem+'.tar.gz');
   with tarfile.open(z,'w:gz') as t:
    for p in unpack.iterdir(): t.add(p,arcname=p.name)
   return z
 raise ValueError(f'{k} → {ext} не поддерживается')
