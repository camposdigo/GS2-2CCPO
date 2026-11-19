"""Prepara cinco arquivos por disciplina, com notebook autossuficiente e verificável.

Os arquivos originais de desenvolvimento são preservados. Dados, fontes e pesos
ficam incorporados como recurso de notebook, sem exibir base64 nas células.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

import nbformat

PRINCIPAL=Path(__file__).resolve().parent.parent
GS=PRINCIPAL.parent
RUNTIME=PRINCIPAL/'.runtime/entregas_enxutas'
TEAM='Gabriel De Biasi Couto — RM 563247\nJoão Pedro da Silva Costa — RM 565031\nRodrigo Campos Cordeiro — RM 566386\nTurma 2CCPO'


BOOTSTRAP='''# Dados e código acompanham este notebook; esta célula prepara os apoios locais.
import base64, hashlib, io, json, os, zipfile
from pathlib import Path

def _preparar_apoios_gs(disciplina):
    candidatos=[]
    for pasta in [Path.cwd(),Path.cwd().parent]:
        candidatos.extend(pasta.glob('*.ipynb'))
    for arquivo in candidatos:
        try:
            recurso=json.loads(arquivo.read_text(encoding='utf-8')).get('metadata',{}).get('recursos_gs',{})
        except (OSError,ValueError):
            continue
        if recurso.get('disciplina')==disciplina:
            break
    else:
        raise FileNotFoundError('Mantenha o arquivo .ipynb na pasta aberta pelo Jupyter/VS Code.')
    conteudo=base64.b64decode(recurso['zip_base64'],validate=True)
    if hashlib.sha256(conteudo).hexdigest()!=recurso['sha256']:
        raise ValueError('O recurso incorporado ao notebook foi alterado.')
    destino=(arquivo.parent/('_apoio_'+disciplina.lower())).resolve()
    destino.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(conteudo)) as pacote:
        for item in pacote.infolist():
            alvo=(destino/item.filename).resolve()
            if not alvo.is_relative_to(destino) or item.is_dir():
                raise ValueError('Caminho inválido no apoio incorporado.')
            dados=pacote.read(item)
            if not alvo.exists() or hashlib.sha256(alvo.read_bytes()).digest()!=hashlib.sha256(dados).digest():
                alvo.parent.mkdir(parents=True,exist_ok=True)
                alvo.write_bytes(dados)
    return destino

GS_APOIO=_preparar_apoios_gs('{subject}')
os.chdir(GS_APOIO)
print('Dados, código e artefatos preparados. As próximas células executam a investigação.')
'''


def payload(root,subject):
    paths=[]
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        rel=p.relative_to(root)
        if any(x in {'.runtime','__pycache__','.venv','.git'} for x in rel.parts):
            continue
        # As fontes, dados e resultados necessários são suficientes para reproduzir.
        if rel.parts[0] not in {'codigo','dados','modelos','resultados','referencias'} and rel.name not in {'equipe.json','requirements.txt'}:
            continue
        if rel.parts[0]=='referencias' and not rel.name.endswith('LICENSE.txt'):
            continue
        if rel.parts[0]=='codigo' and (rel.name.startswith('gerar_') or rel.name.startswith('empacotar')):
            continue
        if rel.name=='EuroSAT.zip':
            continue
        paths.append((rel.as_posix(),p))
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,p in sorted(paths):
            z.writestr(name,p.read_bytes())
    raw=stream.getvalue()
    return {'formato':1,'disciplina':subject,'sha256':hashlib.sha256(raw).hexdigest(),
            'arquivos_de_apoio':len(paths),'zip_base64':base64.b64encode(raw).decode('ascii')}


def make_notebook(root,out,subject,name):
    original=root/f'GS_{subject}_Territorio_Vivo_2CCPO.ipynb'
    nb=nbformat.read(original,as_version=4)
    nb.metadata['recursos_gs']=payload(root,subject)
    intro=nbformat.v4.new_markdown_cell(
        '**Entrega compacta.** Este notebook já contém os resultados e leva os dados, o código'
        +(' e os pesos treinados' if subject=='CNN' else '')+' necessários à reprodução. '
        'Abra o `.ipynb` no Jupyter ou VS Code a partir desta pasta. Ao executar tudo, '
        'a primeira célula prepara automaticamente uma pasta de apoio. '
        'As dependências estão em `requirements.txt`.\n\n'
        +('Para iniciar somente a aplicação, execute `python 03_Aplicacao_CNN_2CCPO.py`; '
          'o modelo já está treinado.\n\n' if subject=='CNN' else '')
        +'Não é necessário executar as células para ler os gráficos e as conclusões já incorporados.')
    # Após a capa, a preparação vem antes da primeira importação de módulos de apoio.
    nb.cells.insert(1,intro)
    nb.cells.insert(2,nbformat.v4.new_code_cell(BOOTSTRAP.replace('{subject}',subject)))
    for cell in nb.cells:
        if cell.cell_type=='markdown':
            cell.source=cell.source.replace('README.md','LEIA_PRIMEIRO.txt')
            cell.source=cell.source.replace('Consulte `GUIA_PARA_EXPLICAR.md`, os slides e o código original.',
                                            'Consulte as explicações, o código deste notebook e os slides.')
        if cell.cell_type=='code':
            cell.execution_count=None
            cell.outputs=[]
    path=out/name
    nbformat.write(nb,path)
    return path


def prepare(subject):
    source=GS/subject/'entrega'
    out=GS/subject/'PARA_ENTREGAR'
    out.mkdir(parents=True,exist_ok=True)
    if subject=='DSA':
        names=['01_Relatorio_DSA_2CCPO.pdf','02_Sintese_Executiva_DSA_2CCPO.pdf',
               '03_Notebook_DSA_2CCPO.ipynb','LEIA_PRIMEIRO.txt','requirements.txt']
        shutil.copy2(source/'Relatorio_DSA_2CCPO.pdf',out/names[0])
        shutil.copy2(source/'Sintese_Executiva_DSA_2CCPO.pdf',out/names[1])
        notebook=make_notebook(source,out,subject,names[2])
        requirements='numpy==2.2.6\nscikit-learn==1.6.1\nmatplotlib==3.10.3\nipykernel==7.4.0\n'
        explanation='''GS DE DATA SCIENCE AND ANALYTICS — 2CCPO

ABRA PRIMEIRO: 01_Relatorio_DSA_2CCPO.pdf (9 páginas).
SÍNTESE OBRIGATÓRIA: 02_Sintese_Executiva_DSA_2CCPO.pdf (1 página).
CÓDIGO E RESULTADOS: 03_Notebook_DSA_2CCPO.ipynb (já executado).

O notebook incorpora os dados reais e o código de apoio.
Para ler os resultados, basta abrir o PDF ou o notebook; não precisa instalar nada.
Para reproduzir com Python 3.12: pip install -r requirements.txt
Abra o notebook no Jupyter/VS Code e execute todas as células.
Os apoios mencionados no relatório são preparados automaticamente pelo notebook.
'''
    else:
        names=['01_Slides_CNN_2CCPO.pdf','02_Notebook_CNN_2CCPO.ipynb',
               '03_Aplicacao_CNN_2CCPO.py','LEIA_PRIMEIRO.txt','requirements.txt']
        shutil.copy2(source/'Slides_CNN_2CCPO.pdf',out/names[0])
        notebook=make_notebook(source,out,subject,names[1])
        launcher='''"""Aplicação CNN da GS — 2CCPO. Instale requirements.txt e execute este arquivo.

O notebook deve ficar ao lado deste script: nele estão o código, os dados e
os pesos treinados. Nenhum treinamento é necessário para abrir a aplicação.
"""\nimport os\nos.chdir(os.path.dirname(os.path.abspath(__file__)))\n'''+BOOTSTRAP.replace('{subject}','CNN')+'''
import runpy,sys
sys.path.insert(0,str(GS_APOIO/'codigo'))
if __name__=='__main__':
    print('Abra http://127.0.0.1:7860 no navegador. Ctrl+C encerra o servidor.')
    runpy.run_path(str(GS_APOIO/'codigo/app.py'),run_name='__main__')
'''
        (out/names[2]).write_text(launcher,encoding='utf-8')
        requirements=(source/'requirements.txt').read_text(encoding='utf-8')
        explanation='''GS DE REDES NEURAIS CONVOLUCIONAIS — 2CCPO

ABRA PRIMEIRO: 01_Slides_CNN_2CCPO.pdf (10 slides).
EXPERIMENTOS E RESULTADOS: 02_Notebook_CNN_2CCPO.ipynb (já executado).
APLICAÇÃO: 03_Aplicacao_CNN_2CCPO.py.

O notebook incorpora as 800 imagens reais, o código e os pesos treinados.
Para ler os resultados, basta abrir os slides ou o notebook.
Para abrir o app com Python 3.12, nesta pasta:
  pip install -r requirements.txt
  python 03_Aplicacao_CNN_2CCPO.py
  Acesse http://127.0.0.1:7860
Não precisa treinar novamente para usar o app. Mantenha os 5 arquivos juntos.
Para reproduzir o treinamento, abra o notebook no Jupyter/VS Code e execute tudo.
'''
    (out/'requirements.txt').write_text(requirements,encoding='utf-8')
    (out/'LEIA_PRIMEIRO.txt').write_text(explanation+'\nINTEGRANTES\n'+TEAM+'\n',encoding='utf-8')
    return out,names,notebook


def verify_notebook(subject,notebook):
    from nbclient import NotebookClient
    temp=RUNTIME/subject
    temp.mkdir(parents=True,exist_ok=True)
    target=temp/notebook.name
    shutil.copy2(notebook,target)
    nb=nbformat.read(target,as_version=4)
    kernel_root=RUNTIME/'jupyter'
    kernel_name='entrega_'+subject.lower()
    spec=kernel_root/'kernels'/kernel_name
    spec.mkdir(parents=True,exist_ok=True)
    python=PRINCIPAL/'modules'/('cnn' if subject=='CNN' else 'water')/'.venv/Scripts/python.exe'
    (spec/'kernel.json').write_text(json.dumps({'argv':[str(python),'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'GS '+subject,'language':'python'}),encoding='utf-8')
    old=os.environ.get('JUPYTER_PATH')
    os.environ['JUPYTER_PATH']=str(kernel_root)+(os.pathsep+old if old else '')
    try:
        client=NotebookClient(nb,timeout=1200,kernel_name=kernel_name,
                              resources={'metadata':{'path':str(temp)}},allow_errors=False)
        client.on_cell_executed=lambda cell,cell_index,execute_reply: print(f'{subject}: célula {cell_index+1} executada',flush=True)
        client.execute()
    finally:
        if old is None:
            os.environ.pop('JUPYTER_PATH',None)
        else:
            os.environ['JUPYTER_PATH']=old
    nbformat.validate(nb)
    code=[c for c in nb.cells if c.cell_type=='code']
    assert [c.execution_count for c in code]==list(range(1,len(code)+1))
    assert not any(o.output_type=='error' for c in code for o in c.outputs)
    images=sum('image/png' in o.get('data',{}) for c in code for o in c.outputs)
    assert images>=5
    nb.metadata['entrega_verificada']={'codigo_executado':len(code),'imagens':images,'erros':0,'recursos_incorporados':True}
    nbformat.write(nb,notebook)
    return {'celulas':len(code),'imagens':images,'erros':0}


def package(subject,out,names):
    for name in names:
        assert (out/name).is_file() and (out/name).stat().st_size>0
    nb=nbformat.read(out/next(n for n in names if n.endswith('.ipynb')),as_version=4)
    assert nb.metadata.get('entrega_verificada',{}).get('erros')==0
    from pypdf import PdfReader
    pdfs={n:len(PdfReader(out/n).pages) for n in names if n.endswith('.pdf')}
    assert list(pdfs.values())==([9,1] if subject=='DSA' else [10])
    dest=GS/subject/f'GS_{subject}_2CCPO.zip'
    if dest.exists() and subject=='DSA':
        backup=dest.parent/'desenvolvimento/GS_DSA_2CCPO_COMPLETO.zip'
        backup.parent.mkdir(exist_ok=True)
        if not backup.exists():
            shutil.copy2(dest,backup)
    temporary=dest.with_suffix('.tmp.zip')
    expected={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in names}
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in names:
            z.write(out/name,arcname=name)
    with zipfile.ZipFile(temporary) as z:
        assert z.namelist()==names and z.testzip() is None
        assert all(hashlib.sha256(z.read(n)).hexdigest()==expected[n] for n in names)
    temporary.replace(dest)
    result={'disciplina':subject,'zip':str(dest),'arquivos_no_zip':len(names),'nomes':names,
            'bytes':dest.stat().st_size,'paginas_pdf':pdfs,'notebook':dict(nb.metadata['entrega_verificada']),'hashes':expected}
    (RUNTIME/f'{subject}_validacao.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('disciplina',choices=['DSA','CNN'])
    parser.add_argument('--somente-empacotar',action='store_true')
    args=parser.parse_args()
    if args.somente_empacotar:
        out=GS/args.disciplina/'PARA_ENTREGAR'
        names=([ '01_Relatorio_DSA_2CCPO.pdf','02_Sintese_Executiva_DSA_2CCPO.pdf','03_Notebook_DSA_2CCPO.ipynb','LEIA_PRIMEIRO.txt','requirements.txt'] if args.disciplina=='DSA' else ['01_Slides_CNN_2CCPO.pdf','02_Notebook_CNN_2CCPO.ipynb','03_Aplicacao_CNN_2CCPO.py','LEIA_PRIMEIRO.txt','requirements.txt'])
    else:
        out,names,notebook=prepare(args.disciplina)
        verify_notebook(args.disciplina,notebook)
    package(args.disciplina,out,names)
