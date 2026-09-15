from __future__ import annotations
import os,tempfile,logging,shutil,zipfile
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update,InlineKeyboardButton as B,InlineKeyboardMarkup as K
from telegram.ext import Application,CommandHandler,MessageHandler,CallbackQueryHandler,ContextTypes,filters
from core import kind, TARGETS, convert, safe_name
load_dotenv(); TOKEN=os.getenv('BOT_TOKEN'); MAX_MB=int(os.getenv('MAX_FILE_MB','50')); logging.basicConfig(level=logging.INFO)

def kb(rows): return K([[B(t,callback_data=d) for t,d in r] for r in rows])
def main_menu(k):
 ts=TARGETS[k]; rows=[]
 for i in range(0,len(ts),3): rows.append([(x.upper(),'cv:'+x) for x in ts[i:i+3]])
 rows += [[('⚙️ Настройки','settings'),('🗜 Сжать','compress')],[('📚 Пакетный режим','batch'),('🗑 Очистить','clear')],[('🏠 Главное меню','home')]]
 return kb(rows)
async def start(u,c):
 await u.message.reply_text('⚡ OmniConvert MAX\n\nУниверсальный конвертер файлов.\nПросто отправь файл или выбери инструмент ↓',reply_markup=kb([[('🔄 Конвертировать файл','ui:convert')],[('🗜 Сжать','ui:compress'),('📚 Объединить','ui:merge')],[('🖼 Изображения','info:image'),('🎬 Видео','info:video')],[('🎵 Аудио','info:audio'),('📄 PDF','info:pdf')],[('📦 Архивы','info:archive'),('⚙️ Настройки','settings')],[('ℹ️ Возможности','help')]]))
async def cancel(u,c):
 c.user_data.clear(); await u.message.reply_text('🧹 Очередь очищена.')
async def mergepdf(u,c): c.user_data['merge']=True;c.user_data['batch_files']=[];await u.message.reply_text('📚 Режим объединения: пришли несколько PDF/картинок по одному, затем нажми /done.')
async def done(u,c):
 files=[Path(x) for x in c.user_data.get('batch_files',[])]
 if not files:return await u.message.reply_text('Очередь пустая.')
 out=files[0].parent/'merged.pdf'
 try:
  from pypdf import PdfWriter
  from PIL import Image
  tmp=[]
  writer=PdfWriter()
  for p in files:
   if p.suffix.lower()=='.pdf': writer.append(str(p))
   else:
    q=p.with_suffix('.pdf'); Image.open(p).convert('RGB').save(q); writer.append(str(q)); tmp.append(q)
  writer.write(str(out)); writer.close()
  with out.open('rb') as f: await u.message.reply_document(f,filename='merged.pdf',caption='✅ Объединено')
 except Exception as e: await u.message.reply_text('❌ '+str(e)[:400])
 c.user_data.clear()
async def receive(u,c):
 m=u.message; obj=(m.document or m.video or m.audio or m.voice or (m.photo[-1] if m.photo else None))
 if not obj:return
 size=getattr(obj,'file_size',0) or 0
 if size>MAX_MB*1024*1024:return await m.reply_text(f'❌ Лимит этой установки: {MAX_MB} МБ.')
 name=safe_name(getattr(obj,'file_name',None) or ('photo.jpg' if m.photo else 'file.bin'))
 td=c.user_data.get('workdir') or tempfile.mkdtemp(prefix='omni_'); c.user_data['workdir']=td
 src=Path(td)/name; await (await obj.get_file()).download_to_drive(src)
 if c.user_data.get('merge') or c.user_data.get('batch_collect'):
  c.user_data.setdefault('batch_files',[]).append(str(src)); return await m.reply_text(f'➕ {name} добавлен. В очереди: {len(c.user_data["batch_files"])}. '+('Пришли ещё или /done.' if c.user_data.get('merge') else 'Пришли ещё, затем выбери формат через /batchdone'))
 k=kind(src)
 if k=='unknown':return await m.reply_text('🤷 Этот формат не удалось распознать.')
 c.user_data['src']=str(src); c.user_data['kind']=k;c.user_data.setdefault('quality',85);c.user_data.setdefault('resolution','original');c.user_data.setdefault('bitrate','auto')
 await m.reply_text(f'📦 {name}\nТип: {k}\nРазмер: {size/1048576:.1f} МБ\n\nЧто делаем?',reply_markup=main_menu(k))
async def batch(u,c): c.user_data['batch_collect']=True;c.user_data['batch_files']=[];await u.message.reply_text('📚 Присылай файлы. Когда закончишь — /batchdone')
async def batchdone(u,c):
 fs=c.user_data.get('batch_files',[])
 if not fs:return await u.message.reply_text('Очередь пустая.')
 common=set(TARGETS[kind(Path(fs[0]))])
 for f in fs[1:]: common &= set(TARGETS.get(kind(Path(f)),[]))
 if not common:return await u.message.reply_text('У этих файлов нет общего формата назначения.')
 c.user_data['batch_collect']=False
 await u.message.reply_text('Во что конвертировать всю очередь?',reply_markup=kb([[ (x.upper(),'bcv:'+x) for x in sorted(common) ]]))
async def callback(u,c):
 q=u.callback_query; await q.answer(); d=q.data
 if d=='home': return await q.edit_message_text('⚡ OmniConvert MAX\n\nОтправь файл или выбери инструмент:',reply_markup=kb([[('🔄 Конвертировать файл','ui:convert')],[('🗜 Сжать','ui:compress'),('📚 Объединить','ui:merge')],[('🖼 Изображения','info:image'),('🎬 Видео','info:video')],[('🎵 Аудио','info:audio'),('📄 PDF','info:pdf')],[('📦 Архивы','info:archive'),('⚙️ Настройки','settings')],[('ℹ️ Возможности','help')]]))
 if d=='ui:convert': return await q.edit_message_text('🔄 Конвертация\n\nПросто отправь мне файл — формат определю автоматически.',reply_markup=kb([[('🏠 Главное меню','home')]]))
 if d=='ui:compress': return await q.edit_message_text('🗜 Сжатие\n\nОтправь файл, затем нажми «Сжать».',reply_markup=kb([[('🏠 Главное меню','home')]]))
 if d=='ui:merge': c.user_data['merge']=True;c.user_data['batch_files']=[];return await q.edit_message_text('📚 Объединение\n\nПришли PDF/картинки по одному, затем /done.',reply_markup=kb([[('🏠 Главное меню','home')]]))
 if d.startswith('info:'):
  k=d.split(':')[1]; return await q.edit_message_text('Поддерживаемые варианты: '+', '.join(x.upper() for x in TARGETS.get(k,[])),reply_markup=kb([[('🏠 Главное меню','home')]]))
 if d=='help': return await q.edit_message_text('ℹ️ OmniConvert MAX\n\nФото • видео • аудио • PDF • документы • архивы\nПакетная обработка: /batch\nОбъединение: /mergepdf\nОчистка: /cancel',reply_markup=kb([[('🏠 Главное меню','home')]]))
 if d=='clear': c.user_data.clear();return await q.edit_message_text('🧹 Удалено.')
 if d=='batch': c.user_data['batch_collect']=True;c.user_data['batch_files']=[];return await q.edit_message_text('📚 Присылай файлы, затем /batchdone')
 if d=='settings':
  return await q.edit_message_text('⚙️ Настройки',reply_markup=kb([[('Качество 60','q:60'),('85','q:85'),('100','q:100')],[('720p','r:720'),('1080p','r:1080'),('Оригинал','r:original')],[('128k','b:128k'),('192k','b:192k'),('Авто','b:auto')],[('⬅️ Назад','back')]]))
 if d=='back': return await q.edit_message_text('Что делаем?',reply_markup=main_menu(c.user_data['kind']))
 if d.startswith(('q:','r:','b:')):
  a,v=d.split(':'); c.user_data[{'q':'quality','r':'resolution','b':'bitrate'}[a]]=int(v) if a=='q' else v; await q.answer('Сохранено',show_alert=False);return
 if d=='compress':
  k=c.user_data['kind']; ext={'image':'webp','video':'mp4','audio':'mp3','pdf':'pdf','document':'pdf','archive':'7z'}.get(k)
  if k=='pdf': return await q.message.reply_text('Для PDF используй конвертацию/извлечение; агрессивное PDF-сжатие зависит от содержимого.')
  c.user_data['quality']=60;c.user_data['bitrate']='128k'; d='cv:'+ext
 if d.startswith('bcv:'):
  ext=d.split(':')[1]; files=[Path(x) for x in c.user_data.get('batch_files',[])]; outdir=files[0].parent/'batchout'; outdir.mkdir(exist_ok=True)
  await q.edit_message_text(f'⚙️ Пакетная конвертация → {ext.upper()}…')
  made=[]
  try:
   for p in files: made.append(await convert(p,ext,outdir,c.user_data.get('quality',85),c.user_data.get('resolution','original'),c.user_data.get('bitrate','auto')))
   z=files[0].parent/'converted.zip'
   with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
    for p in made: zf.write(p,p.name)
   with z.open('rb') as f: await q.message.reply_document(f,filename='converted.zip',caption='✅ Пакет готов')
  except Exception as e: await q.message.reply_text('❌ '+str(e)[:500])
  return
 if d.startswith('cv:'):
  src=Path(c.user_data.get('src','')); ext=d.split(':')[1]
  if not src.exists():return await q.edit_message_text('Файл уже очищен — пришли снова.')
  await q.edit_message_text(f'⚙️ {src.name} → {ext.upper()}…')
  try:
   dst=await convert(src,ext,src.parent/'out',c.user_data.get('quality',85),c.user_data.get('resolution','original'),c.user_data.get('bitrate','auto'))
   if dst.stat().st_size>MAX_MB*1048576:return await q.message.reply_text(f'⚠️ Результат {dst.stat().st_size/1048576:.1f} МБ — больше лимита {MAX_MB} МБ.')
   with dst.open('rb') as f: await q.message.reply_document(f,filename=dst.name,caption='✅ Готово')
  except Exception as e: logging.exception('convert');await q.message.reply_text('❌ '+str(e)[:500])
def main():
 if not TOKEN:raise RuntimeError('Укажи BOT_TOKEN в .env')
 a=Application.builder().token(TOKEN).build();a.add_handler(CommandHandler('start',start));a.add_handler(CommandHandler('cancel',cancel));a.add_handler(CommandHandler('mergepdf',mergepdf));a.add_handler(CommandHandler('done',done));a.add_handler(CommandHandler('batch',batch));a.add_handler(CommandHandler('batchdone',batchdone));a.add_handler(CallbackQueryHandler(callback));a.add_handler(MessageHandler(filters.Document.ALL|filters.VIDEO|filters.AUDIO|filters.VOICE|filters.PHOTO,receive));port=int(os.getenv('PORT','10000')); render_url=os.getenv('RENDER_EXTERNAL_URL'); webhook_path=os.getenv('WEBHOOK_PATH','telegram-webhook'); a.run_webhook(listen='0.0.0.0',port=port,url_path=webhook_path,webhook_url=f'{render_url}/{webhook_path}',drop_pending_updates=True)
if __name__=='__main__':main()
