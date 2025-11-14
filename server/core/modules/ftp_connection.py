import os
from pathlib import Path
from ftplib import FTP, error_perm
import sys


DEBUG_LEVEL = 0  # Nível de depuração padrão
FTP_HOST = "177.154.191.246"
FTP_USER = "dellysns@rgconsultorias.com.br"
FTP_PASS = "&FlgBe59XHqw"

def dprint(message, level=1, file=sys.stderr): # Adiciona file=sys.stderr como padrão aqui
    if DEBUG_LEVEL >= level:
        print(f"[FTP-Connections{level}] {message}", file=file) # Usa o argumento 'file'

def connect_ftp(FTP_HOST, FTP_USER, FTP_PASS):
    try:
        ftp = FTP(FTP_HOST, timeout=30) # Adicionado timeout
        ftp.login(FTP_USER, FTP_PASS)
        dprint("FTP Conectado.", level=2)
        return ftp
    except Exception as e:
        dprint(f"Erro de conexão FTP: {e}", level=1)
        return None

def ftp_ensure_dir(ftp, remote_dir_path_obj: Path):
    remote_dir_str = str(remote_dir_path_obj).replace("\\", "/")
    parts = remote_dir_str.strip('/').split('/')
    current_dir = '/'
    for part in parts:
        if not part: continue
        current_dir = Path(current_dir) / part # Usando Path para juntar corretamente
        try:
            ftp.cwd(str(current_dir).replace("\\", "/"))
        except error_perm:
            try:
                ftp.mkd(str(current_dir).replace("\\", "/"))
                dprint(f"Diretório FTP criado: {current_dir}", level=3)
                ftp.cwd(str(current_dir).replace("\\", "/"))
            except error_perm as e_mkd:
                dprint(f"Falha ao criar/acessar diretório FTP {current_dir}: {e_mkd}", level=1)
                return False
    return True

def ftp_upload_file(ftp, local_filepath_obj: Path, remote_filepath_obj: Path):
    local_filepath_str = str(local_filepath_obj)
    remote_filepath_str = str(remote_filepath_obj).replace("\\", "/")
    remote_dir = Path(remote_filepath_str).parent
    remote_filename = Path(remote_filepath_str).name
    original_dir = ""
    try:
        if ftp and ftp.sock: original_dir = ftp.pwd()
        else: return False
        if not ftp_ensure_dir(ftp, remote_dir):
            dprint(f"Upload FTP falhou: não foi possível garantir o diretório remoto {remote_dir}", level=1)
            if ftp.sock and original_dir: ftp.cwd(original_dir)
            return False
        ftp.cwd(str(remote_dir).replace("\\", "/"))

        with open(local_filepath_str, 'rb') as f:
            ftp.storbinary(f"STOR {remote_filename}", f) # STOR geralmente sobrescreve
        dprint(f"FTP Upload: {local_filepath_str} -> {remote_filepath_str} (Sobrescrito se existia)", level=2)
        if ftp.sock and original_dir: ftp.cwd(original_dir)
        return True
    
    except Exception as e:
        dprint(f"Erro de Upload FTP para {local_filepath_str} -> {remote_filepath_str}: {e}", level=1)
        if ftp.sock and original_dir:
            try: ftp.cwd(original_dir)
            except: pass
        return False
    
def ftp_list_files(ftp, remote_dir_path_obj: Path):
    remote_dir_str = str(remote_dir_path_obj).replace("\\", "/"); original_dir = ""; files = []
    try:
        if ftp and ftp.sock: original_dir = ftp.pwd()
        else: return []
        ftp.cwd(remote_dir_str); files = ftp.nlst()
    except Exception as e: dprint(f"FTP Error listando {remote_dir_str}: {e}", level=2, file=sys.stderr)
    finally:
        if ftp and ftp.sock and original_dir:
            try: ftp.cwd(original_dir)
            except: pass
    return files

def ftp_file_exists(ftp, remote_filepath_obj: Path):
    remote_filepath_str = str(remote_filepath_obj).replace("\\", "/")
    original_dir = ""
    try:
        if not (ftp and ftp.sock): return False
        original_dir = ftp.pwd()
        
        directory = str(Path(remote_filepath_str).parent).replace("\\", "/")
        filename = Path(remote_filepath_str).name
        
        ftp.cwd(directory)
        ftp.size(filename) # Tenta obter o tamanho. Se funcionar, o arquivo existe.
        return True
    except error_perm:
        # O erro esperado quando o arquivo não existe é um '550 No such file or directory'
        return False
    except Exception as e:
        dprint(f"Erro geral verif exist FTP {remote_filepath_str}: {e}", level=2)
        return False # Trata outros erros como 'não existe' por segurança
    finally:
        if ftp and ftp.sock and original_dir:
            try: ftp.cwd(original_dir)
            except: pass

def ftp_find_source_image_in_nobg(ftp, prod_code_str: str, ftp_nobg_dir_path_obj: Path): # Adaptado para esta necessidade
    if not ftp or not ftp.sock: return None
    files_on_ftp = ftp_list_files(ftp, ftp_nobg_dir_path_obj)
    if not files_on_ftp: return None
    # Procura por <prod_code_str>.png ou <prod_code_str>-qualquercoisa.png (ou outras extensões comuns)
    extensions_to_check = ['.png', '.jpg', '.jpeg', '.webp']
    for ftp_filename in files_on_ftp:
        try:
            file_stem = Path(ftp_filename).stem
            file_ext = Path(ftp_filename).suffix.lower()
            if file_stem == prod_code_str and file_ext in extensions_to_check:
                return ftp_filename # Match exato do código com extensão comum
            if file_stem.startswith(f"{prod_code_str}-") and file_ext in extensions_to_check:
                return ftp_filename # Match do código com sufixo
        except Exception: continue
    return None

def limpar_diretorio_ftp(ftp, diretorio_ftp_path_obj: Path):
    """Deleta todos os arquivos dentro de um diretório FTP especificado."""
    if not ftp or not ftp.sock:
        dprint(f"FTP não conectado. Não é possível limpar {diretorio_ftp_path_obj}", level=1, file=sys.stderr)
        return False
    
    remote_dir_str = str(diretorio_ftp_path_obj).replace("\\", "/")
    dprint(f"Tentando limpar diretório FTP: {remote_dir_str}", level=2, file=sys.stderr)
    try:
        original_dir = ftp.pwd()
        ftp.cwd(remote_dir_str) # Entra no diretório
        files_to_delete = ftp.nlst()
        
        # Verifica se nlst() retornou "." e ".." e os remove se necessário
        # (alguns servidores FTP os incluem, outros não)
        files_to_delete = [f for f in files_to_delete if f not in ('.', '..')]

        if not files_to_delete:
            dprint(f"Diretório {remote_dir_str} já está vazio ou não contém arquivos listáveis (além de . e ..).", level=2, file=sys.stderr)
            if ftp.sock and original_dir: ftp.cwd(original_dir)
            return True

        dprint(f"Arquivos a serem deletados em {remote_dir_str}: {files_to_delete}", level=3, file=sys.stderr)
        deleted_count = 0
        for filename in files_to_delete:
            try:
                # Tenta verificar se é um diretório. Se for, pula ou deleta recursivamente (mais complexo).
                # Por simplicidade, vamos assumir que são apenas arquivos.
                # Se ftp.delete(filename) falhar para um diretório, ele levantará uma exceção.
                ftp.delete(filename)
                dprint(f"  Deletado do FTP: {remote_dir_str}/{filename}", level=3, file=sys.stderr)
                deleted_count += 1
            except error_perm as e_del_file:
                # Se for um erro de "não é um arquivo simples" ou "é um diretório", pode ser normal pular.
                # 550 <filename>: Not a plain file. (ocorre ao tentar deletar um diretório com ftp.delete)
                if "550" in str(e_del_file) and ("directory" in str(e_del_file).lower() or "not a plain file" in str(e_del_file).lower()):
                     dprint(f"  Item '{filename}' em {remote_dir_str} é um diretório ou não é um arquivo simples, pulando deleção.", level=3, file=sys.stderr)
                else:
                    dprint(f"  ERRO ao deletar '{filename}' de {remote_dir_str}: {e_del_file}", level=1, file=sys.stderr)
            except Exception as e_gen_del:
                 dprint(f"  ERRO inesperado ao deletar '{filename}' de {remote_dir_str}: {e_gen_del}", level=1, file=sys.stderr)


        if ftp.sock and original_dir: ftp.cwd(original_dir) # Retorna ao diretório original
        dprint(f"Limpeza de {remote_dir_str} concluída. {deleted_count} arquivos deletados.", level=2, file=sys.stderr)
        return True
    except error_perm as e_cwd: # Erro ao entrar no diretório
        dprint(f"ERRO: Não foi possível acessar o diretório {remote_dir_str} para limpeza: {e_cwd}", level=1, file=sys.stderr)
        if ftp.sock and original_dir:
            try: ftp.cwd(original_dir)
            except: pass
        return False
    except Exception as e_list:
        dprint(f"ERRO ao listar/limpar diretório FTP {remote_dir_str}: {e_list}", level=1, file=sys.stderr)
        if ftp.sock and original_dir:
            try: ftp.cwd(original_dir)
            except: pass
        return False

def ftp_download_file(ftp, remote_filepath_obj: Path, local_filepath_obj: Path):
    remote_filepath_str = str(remote_filepath_obj).replace("\\", "/")
    local_filepath_str = str(local_filepath_obj)
    original_dir = ""
    try:
        if ftp and ftp.sock: original_dir = ftp.pwd()
        else: return False
        directory = str(Path(remote_filepath_str).parent).replace("\\", "/")
        filename = Path(remote_filepath_str).name
        dprint(f"Tentando baixar do FTP dir: {directory}, arquivo: {filename}",level=3)
        ftp.cwd(directory)
        with open(local_filepath_str, 'wb') as f:
            ftp.retrbinary(f"RETR {filename}", f.write)
        if ftp.sock and original_dir: ftp.cwd(original_dir)
        dprint(f"FTP Download: {remote_filepath_str} -> {local_filepath_str}", level=2)
        return True
    except Exception as e:
        dprint(f"Erro de Download FTP para {remote_filepath_str} (Destino: {local_filepath_str}): {e}", level=1)
        # traceback.print_exc(file=sys.stdout) # Descomente para debug detalhado de FTP
        if ftp.sock and original_dir:
            try: ftp.cwd(original_dir)
            except: pass
        if Path(local_filepath_str).exists(): # Tenta remover arquivo local parcial
            try: os.remove(local_filepath_str)
            except: pass
        return False
    
def ftp_delete_file(ftp, remote_filepath_obj: Path):
    remote_filepath_str = str(remote_filepath_obj).replace("\\", "/")
    original_dir = ""
    try:
        if ftp and ftp.sock: original_dir = ftp.pwd()
        else: return False
        directory = str(Path(remote_filepath_str).parent).replace("\\", "/")
        filename = Path(remote_filepath_str).name
        ftp.cwd(directory)
        ftp.delete(filename)
        if ftp.sock and original_dir: ftp.cwd(original_dir)
        dprint(f"FTP Deletado: {remote_filepath_str}", level=2)
        return True
    except Exception as e:
        dprint(f"Erro de Deleção FTP para {remote_filepath_str}: {e}", level=1)
        if ftp.sock and original_dir:
            try: ftp.cwd(original_dir)
            except: pass
        return False
