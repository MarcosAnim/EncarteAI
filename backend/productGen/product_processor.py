import os
from shutil import rmtree
import pandas as pd
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont 
import json
import sys
import gc
import traceback
from modules.ftp_connection import connect_ftp, ftp_file_exists, ftp_download_file, ftp_upload_file, ftp_delete_file, ftp_find_source_image_in_nobg

class XlsxLayoutProcessor:
    """
    Classe para processar layouts de produtos individualmente.
    """
    
    # FTP Credentials (should ideally be loaded from environment variables)

    def __init__(self, preset_name: str, FTP_HOST, FTP_USER, FTP_PASS, debug_level: int = 3):
        """
        Inicializa o processador de layouts.
        
        Args:
            preset_name (str): Nome do preset a ser usado (ex: inverno, junino)
                                localizado em xlsx_code/presets/.
            debug_level (int): Nível de debug (0-3).
        """
        self.BASE_DIR = Path(__file__).resolve().parent
        self.DEBUG_LEVEL = debug_level
        self.preset_name = preset_name

        self.FTP_HOST=FTP_HOST
        self.FTP_USER=FTP_USER
        self.FTP_PASS=FTP_PASS

        # Configurações FTP
        self.FTP_PRODUCTS_BASE_NOBG_DIR = "/products"
        self.FTP_MANUAL_NOBG_UPLOAD_DIR = "/temp/nobg_images"
        
        # Diretório temporário local
        self.LOCAL_TEMP_PROCESSING_DIR = self.BASE_DIR / "temp_processing_ftp_files"
        self.LOCAL_TEMP_PROCESSING_DIR.mkdir(parents=True, exist_ok=True) # Ensure it exists
        
        # Cores e configurações (Moved to instance attributes for consistency)
        self.branco = (255,255,255)
        self.verde_neon = (108, 172, 28)
        self.azul = (10, 77, 155)
        self.preto = (0,0,0)
        self.dark_blue = (10, 33, 81)
        self.black_grey = (51, 51, 51)
        
        # Configuração dos diretórios de preset
        self.PRESET_DIR = self.BASE_DIR / "presets" / preset_name
        #self.PRESET_DIR_DINAMIC = self.PRESET_DIR / 'oferta personalizada' # Used for 'destaque' layouts
        
        # Carregar marcas
        self.marcas = self._load_marcas_from_json()
        
        # Verificar se diretórios existem
        self._validate_directories()
        
        # Conexão FTP (será estabelecida quando necessário)
        self.ftp_conn = None
        
    def process_product_to_memory(self, prod_code: int, preco, descricao: str, client: str = "dellys", 
                                 obs: str = None, tipo: str = None, selo: str = None,
                                 is_destaque: bool = False) -> bytes | None:
        """
        Processa um produto e retorna os bytes da imagem gerada em memória (formato PNG).
        Ideal para uso em APIs.
        """
        pil_image_base = None
        temp_file_path = None
        layout_image_obj = None

        self._dprint(f"\n--- Processando Produto (em memória): {prod_code} ---", level=1)
        
        try:
            # 1. Obter a imagem base do produto
            pil_image_base, temp_file_path, source = self._get_product_image(prod_code)
            if pil_image_base is None:
                self._dprint(f"!!! {prod_code}: Imagem base não encontrada. Não é possível gerar layout.", level=1, file=sys.stderr)
                return None

            # 2. Carregar configurações
            fonts_config = self._load_fonts_config(client)
            
            # Caminho de saída temporário, necessário para a função _generate_layout
            # Mas não nos importamos com o arquivo salvo, queremos o objeto retornado.
            temp_output_path = self.LOCAL_TEMP_PROCESSING_DIR / f"temp_api_{prod_code}.png"

            # 3. Gerar o layout e obter o objeto PIL
            # Precisamos garantir que _generate_layout retorne o objeto da imagem
            layout_image_obj = self._generate_layout(
                prod_code=prod_code,
                pil_image_base=pil_image_base,
                preco=preco,
                descricao=descricao,
                client=client,
                obs=obs,
                tipo=tipo,
                selo=selo,
                output_path=temp_output_path,
                is_destaque=is_destaque,
                fonts_config=fonts_config
            )

            if not layout_image_obj:
                self._dprint(f"Falha ao gerar o objeto de imagem para {prod_code}.", level=1, file=sys.stderr)
                return None
            
            # 4. Converter o objeto de imagem para bytes em um buffer de memória
            import io
            buffer = io.BytesIO()
            layout_image_obj.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()
            
            self._dprint(f"Layout para {prod_code} gerado com sucesso em memória.", level=2)
            return image_bytes

        except Exception as e:
            self._dprint(f"ERRO ao gerar imagem em memória para {prod_code}: {e}", level=1, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return None
        finally:
            # --- Limpeza Crucial ---
            if layout_image_obj: layout_image_obj.close()
            if pil_image_base: pil_image_base.close()
            if temp_file_path and temp_file_path.exists():
                try: os.remove(temp_file_path)
                except OSError: pass
            gc.collect()

    def _validate_directories(self):
        """Valida se os diretórios necessários existem."""
        if not self.PRESET_DIR.exists():
            raise FileNotFoundError(f"Diretório de preset '{self.PRESET_DIR}' não encontrado. Verifique se '{self.preset_name}' é um nome de pasta válido em '{self.BASE_DIR / 'presets'}'.")
        
        fonts_dir = self.BASE_DIR / 'fonts'
        if not fonts_dir.exists():
            raise FileNotFoundError(f"Diretório de fontes '{fonts_dir}' não encontrado.")
    
    def _load_marcas_from_json(self, json_file: Path = None) -> list: # type: ignore
        """Carrega marcas do arquivo JSON."""
        if json_file is None:
            json_file = self.BASE_DIR / "marcas.json"
            
        marcas_padrao = ["faz & forno","chef's own", "chef&co","chef e co", "chef & co", 
                        "d´accord", "fritz & frida","mr. fries","mr.fries",
                        "raízes de minas","porto alegre", "grand minas", "pastry pride", "mar e mar"]
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._dprint(f"Marcas carregadas de '{json_file}'.", level=3)
            return data.get("marcas", marcas_padrao)
        except FileNotFoundError:
            self._dprint(f"Arquivo de marcas '{json_file}' não encontrado. Usando marcas padrão.", level=2)
            return marcas_padrao
        except json.JSONDecodeError:
            self._dprint(f"Erro ao decodificar JSON de marcas '{json_file}'. Usando marcas padrão.", level=2)
            return marcas_padrao
    
    def _dprint(self, message: str, level: int = 1, file=sys.stderr):
        """Debug print."""
        if self.DEBUG_LEVEL >= level:
            print(f"\033[33m[Layout-Processor{level}] {message}\033[0m", file=file)
    
    def _ensure_ftp_connection(self) -> bool:
        """Garante que a conexão FTP está estabelecida."""
        if self.ftp_conn is None:
            try:
                self.ftp_conn = connect_ftp(self.FTP_HOST, self.FTP_USER, self.FTP_PASS)
                if self.ftp_conn:
                    self._dprint("Conexão FTP estabelecida.", level=3)
                else:
                    self._dprint("Falha ao estabelecer conexão FTP.", level=1, file=sys.stderr)
            except Exception as e:
                self._dprint(f"Erro ao conectar ao FTP: {e}", level=1, file=sys.stderr)
                self.ftp_conn = None
        return self.ftp_conn is not None
    
    def _load_fonts_config(self, client: str) -> dict:
        """Carrega configuração de fontes baseada no cliente."""
        fonts_config = {}

        fonts_config_path = self.PRESET_DIR / "fonts_config.json"
            
        if fonts_config_path.exists():
            try:
                with open(fonts_config_path, 'r', encoding='utf-8') as f:
                    fonts_config = json.load(f)
                self._dprint(f"Configurações de fonte carregadas de: {fonts_config_path}", level=2)
            except json.JSONDecodeError:
                self._dprint(f"ERRO: Falha ao decodificar fonts_config.json em {fonts_config_path}. Usando fontes padrão/fallback.", level=1, file=sys.stderr)
            except Exception as e:
                self._dprint(f"ERRO ao carregar fonts_config.json: {e}. Usando fontes padrão/fallback.", level=1, file=sys.stderr)
        else:
            self._dprint(f"AVISO: fonts_config.json não encontrado em {fonts_config_path}. Usando fontes padrão/fallback.", level=2)
            
        return fonts_config
    
    def resize_ar(self, img: Image.Image, x_resize: int, limitx: int, limity: int) -> tuple[int, int]:
        """
        Redimensiona imagem mantendo proporção.

        Args:
            img (Image.Image): Imagem PIL a ser redimensionada.
            x_resize (int): Largura alvo inicial para redimensionamento.
            limitx (int): Largura máxima permitida.
            limity (int): Altura máxima permitida.

        Returns:
            tuple[int, int]: (nova_largura, nova_altura) mantendo proporção e respeitando limites.
        """
        can_x, can_y = limitx, limity
        x, y = img.width, img.height

        # Evita divisão por zero ou imagem inválida
        if x == 0 or y == 0: 
            return can_x, can_y

        # Calcula altura proporcional à largura desejada
        y_resize_float = (x_resize * y) / x

        # Se largura excede limite, ajusta largura e recalcula altura proporcional
        if x_resize > can_x:
            x_resize_new = can_x
            y_resize_float = (x_resize_new * y) / x
            x_resize = x_resize_new

        # Se altura excede limite, ajusta altura e recalcula largura proporcional
        if y_resize_float > can_y:
            y_resize_new = can_y
            x_resize = int((y_resize_new * x) / y)
            y_resize_float = float(y_resize_new)

        # Retorna dimensões finais como inteiros
        return int(x_resize), int(y_resize_float)
    
    def trim_transparent_border(self, image: Image.Image) -> Image.Image:
        """Remove bordas transparentes da imagem."""
        if image.mode != 'RGBA': 
            image = image.convert("RGBA")
        bbox = image.getbbox()
        return image.crop(bbox) if bbox else image.copy()
    
    def get_text_width_pixels(self, text: str, font: ImageFont.FreeTypeFont) -> int:
        """
        Calcula a largura do texto em pixels usando PIL.
        
        Args:
            text: Texto para medir
            font_path: Caminho para o arquivo da fonte (opcional)
            font_size: Tamanho da fonte em pontos
        
        Returns:
            Largura do texto em pixels
        """
        font_size = font.size
        try:
            
            # Cria uma imagem temporária para medir o texto
            img = Image.new('RGB', (1, 1))
            draw = ImageDraw.Draw(img)
            
            # Obtém as dimensões do texto
            bbox = draw.textbbox((0, 0), text, font=font)
            width = bbox[2] - bbox[0]
            
            return int(width)
        
        except Exception:
            # Fallback: estimativa baseada no tamanho da fonte
            # Aproximação: largura média de caractere = font_size * 0.6
            return int(len(text) * font_size * 0.6)

    def linebk_pixels(self, description: str, max_width_pixels: int, font:ImageFont.FreeTypeFont, 
                    tolerancia_pixels: int = 0) -> list:
        """
        Quebra o nome do produto em linhas baseado na largura em pixels.
        
        Args:
            nome_produto: Texto a ser quebrado
            max_width_pixels: Largura máxima em pixels por linha
            font_path: Caminho para o arquivo da fonte
            font_size: Tamanho da fonte em pontos
            tolerancia_pixels: Tolerância em pixels para ultrapassar a largura máxima
        
        Returns:
            Lista de strings com as linhas quebradas
        """
        nome_produto_lower = description.lower()
        palavras = nome_produto_lower.split()
        resultado, linha_atual, i = [], [], 0

        while i < len(palavras):
            palavra_atual = palavras[i]
            
            # Check for multi-word brands
            marca_encontrada_neste_passo = False
            for marca_item in self.marcas or []:
                marca_palavras = marca_item.split()
                if palavras[i : i + len(marca_palavras)] == marca_palavras:
                    palavra_atual = " ".join(marca_palavras)
                    i += len(marca_palavras) - 1
                    marca_encontrada_neste_passo = True
                    break

            # Monta o texto da linha atual com a nova palavra
            if linha_atual:
                texto_teste = " ".join(linha_atual + [palavra_atual])
            else:
                texto_teste = palavra_atual
            
            # Mede a largura em pixels do texto
            largura_pixels = self.get_text_width_pixels(texto_teste, font)

            # Se ultrapassar a largura máxima + tolerância, quebra a linha
            if linha_atual and largura_pixels > max_width_pixels + tolerancia_pixels:
                resultado.append(" ".join(linha_atual))
                linha_atual = [palavra_atual]
            else:
                linha_atual.append(palavra_atual)
            
            i += 1

        # Adiciona a última linha se houver conteúdo
        if linha_atual:
            resultado.append(" ".join(linha_atual))

        # Evitar última linha com 1 só palavra
        if len(resultado) >= 2:
            ult_linha = resultado[-1].split()
            penult_linha = resultado[-2].split()

            if len(ult_linha) == 1:
                palavra_sobrando = ult_linha[0]
                texto_combinado = " ".join(penult_linha + [palavra_sobrando])
                largura_combinada = self.get_text_width_pixels(texto_combinado, font)
                
                if largura_combinada <= max_width_pixels + tolerancia_pixels:
                    # Pode juntar as linhas
                    resultado[-2] = texto_combinado
                    resultado.pop()
                else:
                    # Tenta redistribuir melhor
                    combinadas = penult_linha + ult_linha
                    nova_linha1, nova_linha2 = [], []
                    
                    for p in combinadas:
                        texto_teste = " ".join(nova_linha1 + [p])
                        largura_teste = self.get_text_width_pixels(texto_teste, font)
                        
                        if largura_teste <= max_width_pixels:
                            nova_linha1.append(p)
                        else:
                            nova_linha2.append(p)
                    
                    # Reconstrói as duas últimas linhas
                    resultado = resultado[:-2]
                    resultado.append(" ".join(nova_linha1))
                    if nova_linha2:
                        resultado.append(" ".join(nova_linha2))
        self._dprint(f"Max width: {max_width_pixels}, lines: {[line.upper() for line in resultado]}", level=1)

        return [line.upper() for line in resultado]
    
    def _get_product_image(self, prod_code: int):
        """Busca imagem do produto no FTP."""
        if not self._ensure_ftp_connection():
            self._dprint("FTP não conectado. Não é possível buscar imagem.", level=1, file=sys.stderr)
            return None, None, "FTP Desconectado"
        
        standard_product_img_filename = f"{prod_code}.png"
        local_temp_file_path = None
        pil_image = None
        source = "Nenhuma"
        
        # Ensure temp directory exists
        self.LOCAL_TEMP_PROCESSING_DIR.mkdir(parents=True, exist_ok=True)
        
        try:
            # FLUXO 1: Imagem manual nobg (uploaded for correction)
            self._dprint(f"     Verificando FTP (manual nobg) para produto {prod_code}...", level=3)
            found_filename = ftp_find_source_image_in_nobg(self.ftp_conn, str(prod_code), 
                                                         Path(self.FTP_MANUAL_NOBG_UPLOAD_DIR))
            
            if found_filename:
                ftp_path = Path(self.FTP_MANUAL_NOBG_UPLOAD_DIR) / found_filename
                local_temp_download_path = self.LOCAL_TEMP_PROCESSING_DIR / f"manual_dl_{found_filename}"
                local_trimmed_path = self.LOCAL_TEMP_PROCESSING_DIR / f"trimmed_{standard_product_img_filename}"
                
                if ftp_download_file(self.ftp_conn, ftp_path, local_temp_download_path):
                    with Image.open(local_temp_download_path) as img_manual:
                        pil_image = self.trim_transparent_border(img_manual.copy())
                    
                    pil_image.save(str(local_trimmed_path), "PNG") # Save trimmed version
                    source = "FTP_MANUAL_NOBG_UPLOAD_DIR (promovido)"
                    self._dprint(f"     Imagem de {self.FTP_MANUAL_NOBG_UPLOAD_DIR} processada para base.",level=2)
                    
                    # Promote to base bank
                    if ftp_upload_file(self.ftp_conn, local_trimmed_path, 
                                     Path(self.FTP_PRODUCTS_BASE_NOBG_DIR) / standard_product_img_filename):
                        ftp_delete_file(self.ftp_conn, ftp_path) # Delete from manual after promoting
                        self._dprint(f"     Imagem {found_filename} promovida para banco base e deletada do manual.",level=2)
                    
                    local_temp_file_path = local_trimmed_path # This is now the source for PIL, cleanup later
                    # pil_image should be returned and closed by the caller
                    
                else: raise Exception("Falha ao baixar imagem do manual nobg")
            
            # FLUXO 2: Imagem do banco base (if not found in manual or manual failed)
            if pil_image is None: 
                ftp_path_base = Path(self.FTP_PRODUCTS_BASE_NOBG_DIR) / standard_product_img_filename
                self._dprint(f"     Verificando banco base '{self.FTP_PRODUCTS_BASE_NOBG_DIR}' para {standard_product_img_filename}...", level=3)
                
                if ftp_file_exists(self.ftp_conn, ftp_path_base):
                    local_temp_download_path = self.LOCAL_TEMP_PROCESSING_DIR / f"base_dl_{standard_product_img_filename}"
                    
                    if ftp_download_file(self.ftp_conn, ftp_path_base, local_temp_download_path):
                        pil_image = Image.open(local_temp_download_path)
                        source = "FTP_PRODUCTS_BASE_NOBG_DIR"
                        self._dprint(f"     Imagem do banco base carregada para produto {prod_code}.", level=2)
                        local_temp_file_path = local_temp_download_path # This is now the source for PIL
                    else: 
                        self._dprint(f"     Falha ao baixar img base de {self.FTP_PRODUCTS_BASE_NOBG_DIR}.",level=1)
                else: 
                    self._dprint(f"     Imagem base não encontrada em {self.FTP_PRODUCTS_BASE_NOBG_DIR}.",level=3)
                        
        except Exception as e:
            self._dprint(f"ERRO ao buscar imagem do produto {prod_code}: {e}", level=1, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            if pil_image: pil_image.close()
            pil_image = None # Ensure pil_image is None on error
        finally:
            # Clean up intermediate downloaded files, but keep the one that `pil_image` refers to
            # `local_temp_download_path` might refer to the actual image opened or a temporary trimmed copy
            if 'local_temp_download_path' in locals() and local_temp_download_path and local_temp_download_path.exists() and local_temp_file_path != local_temp_download_path:
                try: os.remove(local_temp_download_path)
                except OSError: pass

        return pil_image, local_temp_file_path, source
    
    def process_product(self, prod_code: int, preco, descricao: str, client: str = "dellys", 
                       obs: str = None, tipo: str = None, selo: str = None, output_dir: Path = None,  # type: ignore
                       is_destaque: bool = False, force_recreate: bool = False) -> str:
        """
        Processa um produto individual e gera seu layout.
        
        Args:
            prod_code: Código do produto (int)
            preco: Preço do produto (float ou str "R$X,XX")
            descricao: Descrição do produto (str)
            client: Cliente ("dellys" ou "ns")
            obs: Observação opcional (str)
            tipo: Tipo/unidade do produto (str, ex: "KG", "UN")
            selo: Selos do produto (str, ex: "ME, ST, EXCLUSIVO NO SITE")
            output_dir: Caminho do diretório de saída para o layout. Se None, usa BASE_DIR / "output".
            is_destaque: Se é produto de destaque (true para o primeiro item, false para os demais)
            force_recreate: Forçar recriação mesmo se arquivo existir
            
        Returns:
            str: Caminho do layout gerado ou None se falhou
        """
        try:
            if output_dir is not None:
                output_dir = Path(output_dir)
        except Exception as e:
            self._dprint(f"Caminho de output_dir inválido: {output_dir}. Erro: {e}", level=1, file=sys.stderr)
            return None

        self._dprint(f"\n--- Processando Produto: {prod_code} (Destaque: {is_destaque}) ---", level=1)
        
        # Validar código do produto
        if not isinstance(prod_code, int):
            try: prod_code = int(prod_code)
            except (ValueError, TypeError):
                self._dprint(f"Código de produto inválido: '{prod_code}'. Deve ser um número inteiro.", level=1, file=sys.stderr)
                return None
        
        # Definir caminho de saída
        if output_dir is None:
            output_dir = self.BASE_DIR / "output"
        
        output_path = output_dir / f"{prod_code}.png"
        
        # Criar diretório de saída
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Verificar se já existe e não é para recriar
        if output_path.exists() and not force_recreate:
            self._dprint(f"  Layout já existe em '{output_path}' para produto {prod_code}. Usando existente.", level=2)
            return str(output_path)
        
        # Buscar imagem do produto
        pil_image_base, temp_file_path, source = None, None, "Nenhuma"
        try:
            pil_image_base, temp_file_path, source = self._get_product_image(prod_code)
        except Exception as e:
            self._dprint(f"ERRO ao tentar obter imagem para {prod_code}: {e}", level=1, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            
        if pil_image_base is None:
            self._dprint(f"!!! {prod_code}: NENHUMA IMAGEM BASE DISPONÍVEL (Fonte: {source}, FTP: {'Conectado' if self.ftp_conn else 'Desconectado'}). Pulando montagem.", level=1, file=sys.stderr)
            if temp_file_path and temp_file_path.exists():
                try: os.remove(temp_file_path)
                except OSError: pass
            return None # type: ignore
        
        layout_obj = None
        try:
            # Carregar configurações de fonte
            fonts_config = self._load_fonts_config(client)
            
            # Gerar o layout
            self._dprint(f"  Montando layout para {prod_code} (base de: {source})...", level=2)
            layout_obj = self._generate_layout(
                prod_code=prod_code,
                pil_image_base=pil_image_base,
                preco=preco,
                descricao=descricao,
                client=client,
                obs=obs,
                tipo=tipo,
                selo=selo,
                output_path=output_path,
                is_destaque=is_destaque,
                fonts_config=fonts_config
            )
            
            if layout_obj:
                layout_obj.close()
                self._dprint(f"Layout gerado com sucesso para produto {prod_code}: {layout_obj}", level=1)
                return str(output_path)
            else:
                self._dprint(f"Falha na geração do layout para produto {prod_code}.", level=1, file=sys.stderr)
                return None
            
        except Exception as e:
            self._dprint(f"ERRO ao gerar layout para produto {prod_code}: {e}", level=1, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            layout_obj = None
            
        finally:
            # Limpeza: fecha a imagem base e remove o arquivo temporário
            if pil_image_base: pil_image_base.close()
            if temp_file_path and temp_file_path.exists():
                try: os.remove(temp_file_path)
                except OSError: pass
            gc.collect() # Force garbage collection
            self._dprint(f"--- {prod_code} Processamento Concluído. Status: {'Sucesso' if layout_obj else 'Falha'}. ---", level=2)
        
        return layout_obj # type: ignore
            
    def _generate_layout(self, prod_code: int, pil_image_base: Image.Image, preco, descricao: str, client: str, 
                        obs: str, tipo: str, selo: str, output_path: Path, is_destaque: bool, fonts_config: dict) -> str:
        """Gera o layout do produto (parte central da lógica)."""
        
        final_layout_pil_obj = None
        image_layout_template_pil = None
        prbar_img = None
        obs_bar_img_pil = None # Ensure all opened images are tracked for closing
        
        try:
            # Convert preco to float early for checks
            preco_val_float = 0.0
            try:
                if isinstance(preco, str): preco_val_float = float(preco.replace("R$", "").replace(",", ".").strip())
                else: preco_val_float = float(preco)
            except (ValueError, TypeError):
                self._dprint(f"AVISO {prod_code}: Preço '{preco}' não numérico. Usando 0.00.", level=1)
                preco_val_float = 0.0

            # Configurações baseadas no cliente e se é destaque

            layout_base_filename = 'Layout.png'
            obs_bar_filename = "obs_bar.png"
            preco_bar_filename =  "Preco_bar.png"
            st_img_filename = "ST.png"
            layout_template_path = self.PRESET_DIR / layout_base_filename
            img_resize_params = (370, 550, 600)
            img_offset = (0, 0)
            line_gap = 20
            
            # Carregar imagens base
            try:
                image_layout_template_pil = Image.open(layout_template_path)
                prbar_img_path = self.PRESET_DIR / preco_bar_filename
                prbar_img = Image.open(prbar_img_path)
                main_size = image_layout_template_pil.size
                prbar_new_size = self.resize_ar(prbar_img, int(main_size[0]*0.5), main_size[0]*1, main_size[1]*1)
                prbar_img = prbar_img.resize(prbar_new_size, Image.Resampling.LANCZOS)
            except FileNotFoundError as e:
                raise FileNotFoundError(f"Um arquivo de template ou barra de preço não foi encontrado: {e}")
            
            # Redimensionar imagem do produto
            img_prod_resized_x, img_prod_resized_y = self.resize_ar(
                pil_image_base, img_resize_params[0], img_resize_params[1], img_resize_params[2]
            )
            
            # Criar layout final
            final_layout_pil_obj = Image.new("RGBA", image_layout_template_pil.size, (0,0,0,0))
            draw_context = ImageDraw.Draw(final_layout_pil_obj)
            final_layout_pil_obj.paste(image_layout_template_pil, (0,0))
            
            # Y - X (inverted for PIL)
            info_pos = (350, 20)
            value_img = (0, -80)
            legend_pos = (400, 0)

            # Colar imagem do produto
            with pil_image_base.resize((img_prod_resized_x, img_prod_resized_y), Image.Resampling.LANCZOS) as fi_resized:
                altura_img_prod = ((final_layout_pil_obj.height - fi_resized.height) // 2)
                largura_img_prod = (final_layout_pil_obj.width - fi_resized.width) // 2
                final_layout_pil_obj.paste(fi_resized, 
                                 (largura_img_prod + value_img[0] + img_offset[0], 
                                  altura_img_prod + value_img[1] + img_offset[1]), 
                                 mask=fi_resized)
            
            # Configurar fontes
            fonts_system_dir = self.BASE_DIR / 'fonts'
            font_configs = self._get_font_configs(fonts_config, prbar_img.size, preco)
            fonts = self._load_fonts(fonts_system_dir, font_configs, preco_val_float)
            
            # Posições para elementos de texto e barras
            bar_pos_x = info_pos[1]
            bar_pos_y = info_pos[0]
            prbar_x_size, prbar_y_size = prbar_img.size
            
            # Colar barra de preço
            final_layout_pil_obj.paste(prbar_img, (bar_pos_x, bar_pos_y), mask=prbar_img)
            
            # Adicionar texto da descrição
            self._add_description_text(draw_context, descricao, legend_pos[1], legend_pos[0], main_size[0], 70,
                                    prbar_y_size, fonts['description'], font_configs['description']['color'])
            
            # Adicionar preço
            cif_final_pos = self._add_price_text(draw_context, preco_val_float, tipo, bar_pos_x, bar_pos_y, 
                                               prbar_x_size, prbar_y_size, fonts, font_configs)
            
            # Adicionar selos
            #self._add_seals(final_layout_pil_obj, selo, is_destaque, client, cif_final_pos, st_img_filename)
            
            # Adicionar observações


            # Salvar layout
            #final_layout_pil_obj.save(str(output_path))
            return final_layout_pil_obj
            
        except Exception as e:
            self._dprint(f"ERRO CRÍTICO na montagem do layout para {prod_code}: {e}", level=1, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return None # type: ignore
        
        finally:
            # Cleanup PIL Image objects
            if image_layout_template_pil: image_layout_template_pil.close()
            if prbar_img: prbar_img.close()
            #if final_layout_pil_obj: final_layout_pil_obj.close()
            if obs_bar_img_pil: obs_bar_img_pil.close()

    def _get_font_configs(self, fonts_config: dict, main_size, preco) -> dict:
        """Extrai configurações de fonte baseado se é destaque."""
        suffix = ""

        paser_price = preco.replace("R$", "").replace( ".", ",")

        configs = {
            'description': fonts_config.get("fonts", {}).get(f"description{suffix}", {}),
            'price': fonts_config.get("fonts", {}).get(f"price{suffix}", {}),
            'observation': fonts_config.get("fonts", {}).get(f"obsevation{suffix}", {}),  # Note: 'obsevation' no original
            'percentage': fonts_config.get("fonts", {}).get(f"porcentage{suffix}", {}),   # Note: 'porcentage' no original
        }
        
        # Apply default values if not specified in config
        for config_name, config in configs.items():
            if 'font-name' not in config:
                config['font-name'] = 'Arial'  # Default font
            if 'font-color' not in config:
                config['font-color'] = [0, 0, 0]  # Default black color
            config['color'] = tuple(config['font-color']) # Convert list to tuple for PIL
            
            # Ensure font sizes have defaults if missing
            if config_name == 'description': config.setdefault('font-size', 14)
            elif config_name == 'price':
                font_file_path = str(self.BASE_DIR / 'fonts' / f"{config['font-name']}.ttf")
                test_font_size= self.set_font_size(paser_price, main_size, font_file_path)
                config.setdefault('real-size', int(test_font_size*0.7))
                config.setdefault('cent-size', int(test_font_size*0.4))
                config.setdefault('unit-size', int(test_font_size*0.15))
            elif config_name == 'observation': config.setdefault('size', 10)
            elif config_name == 'percentage':
                config.setdefault('porcentage-size', 20)
                config.setdefault('description-size', 12)
                config.setdefault('unit-size', 10)
        
        return configs
    
    def _load_fonts(self, fonts_dir: Path, font_configs: dict, preco_val_float: float) -> dict:
        """Carrega os objetos de fonte."""
        size_adjustment = 10 if preco_val_float > 99 else 12
        
        fonts = {}
        
        # Fonte da descrição
        desc_config = font_configs['description']
        fonts['description'] = ImageFont.truetype(
            str(fonts_dir / f"{desc_config['font-name']}.ttf"), 
            desc_config['font-size']
        )
        
        # Fontes do preço
        price_config = font_configs['price']
        fonts['price_real'] = ImageFont.truetype(
            str(fonts_dir / f"{price_config['font-name']}.ttf"), 
            price_config['real-size'] + size_adjustment
        )
        fonts['price_cent'] = ImageFont.truetype(
            str(fonts_dir / f"{price_config['font-name']}.ttf"), 
            price_config['cent-size'] + size_adjustment
        )
        fonts['price_unit'] = ImageFont.truetype(
            str(fonts_dir / f"{price_config['font-name']}.ttf"), 
            price_config['unit-size'] + int(size_adjustment + size_adjustment * 0.5)
        )
        
        # Fonte da observação
        obs_config = font_configs['observation']
        fonts['observation'] = ImageFont.truetype(
            str(fonts_dir / f"{obs_config['font-name']}.ttf"), 
            obs_config['size']
        )
        
        # Fontes da porcentagem
        pct_config = font_configs['percentage']
        fonts['percentage_value'] = ImageFont.truetype(
            str(fonts_dir / f"{pct_config['font-name']}.ttf"), 
            pct_config['porcentage-size']
        )
        fonts['percentage_desc'] = ImageFont.truetype(
            str(fonts_dir / f"{pct_config['font-name']}.ttf"), 
            pct_config['description-size']
        )
        fonts['percentage_unit'] = ImageFont.truetype(
            str(fonts_dir / f"{pct_config['font-name']}.ttf"), 
            pct_config['unit-size']
        )
        
        return fonts
    
    def _add_description_text(self, draw: ImageDraw.ImageDraw, descricao: str, bar_pos_x: int, bar_pos_y: int, 
                            prbar_x_size: int, border: int, prbar_y_size: int, font: ImageFont.FreeTypeFont, color: tuple, 
                            line_gap = None):
        """Adiciona texto da descrição ao layout."""
        limit_width = int(prbar_x_size * (border/100))
        self._dprint(f"border: {border}%, prbar_x_size: {limit_width}px", level=1)
        
        lines = self.linebk_pixels(descricao, limit_width, font= font, tolerancia_pixels=0)
        
        reversed_lines = lines[::-1]
        if line_gap:
            line_gap = line_gap
        else:
            font_size = font.size
            line_gap = int(font_size * 1) # Espaçamento entre linhas baseado no tamanho da fonte

        # Calculate total text height based on lines and gaps
        text_total_height = len(reversed_lines) * line_gap
        line_height_accumulator = 0
        
        # Position for the first line (bottom-most)
        leg_y_start = (bar_pos_y + prbar_y_size + text_total_height)
        
        for line_text in reversed_lines:
            draw.text((bar_pos_x + (prbar_x_size/2), leg_y_start - line_height_accumulator), 
                     line_text, font=font, anchor='mm', fill=color)
            line_height_accumulator += line_gap
    
    def _add_price_text(self, draw: ImageDraw.ImageDraw, preco_val_float: float, tipo: str, bar_pos_x: int, 
                       bar_pos_y: int, prbar_x_size: int, prbar_y_size: int, fonts: dict, font_configs: dict) -> tuple[int, int]:
        """Adiciona texto do preço ao layout e retorna a posição do cifrão para selos."""
        
        is_percentage = 0 < preco_val_float < 0.40
        price_font_color = font_configs['price']['color']
        cif_final_pos = (0, 0) # Default position if not calculated
        
        if not is_percentage:
            # Preço normal
            preco_str_fmt = '{:0.2f}'.format(preco_val_float)
            reais_part, centavos_part_full = preco_str_fmt.split('.')
            centavos_part_val = "," + centavos_part_full
            
            # Measure text dimensions
            reais_bbox = draw.textbbox((0,0), reais_part, font=fonts['price_real'], anchor="ls") # anchor='ls' for proper height measurement from baseline
            reais_w = reais_bbox[2] - reais_bbox[0]
            reais_h = fonts['price_real'].getbbox(reais_part)[3] - fonts['price_real'].getbbox(reais_part)[1]
            
            centavos_bbox = draw.textbbox((0,0), centavos_part_val, font=fonts['price_cent'], anchor="lb")
            centavos_w = centavos_bbox[2] - centavos_bbox[0]
            centavos_h = fonts['price_cent'].getbbox(centavos_part_val)[3] - fonts['price_cent'].getbbox(centavos_part_val)[1]

            cifrao_str = "R$"
            cifrao_bbox = draw.textbbox((0,0), cifrao_str, font=fonts['price_unit'], anchor="lt")
            cifrao_w = cifrao_bbox[2] - cifrao_bbox[0]
            cifrao_h = fonts['price_unit'].getbbox(cifrao_str)[3] - fonts['price_unit'].getbbox(cifrao_str)[1]
            
            tip_val_rendered = str(tipo).upper() if tipo else ""
            tip_w, tip_h = 0, 0
            if tip_val_rendered:
                tip_bbox = draw.textbbox((0,0), tip_val_rendered, font=fonts['price_unit'], anchor="lt")
                tip_w = tip_bbox[2] - tip_bbox[0]
                tip_h = fonts['price_unit'].getbbox(tip_val_rendered)[3] - fonts['price_unit'].getbbox(tip_val_rendered)[1]

            # Calculate total width for price components (R$, Reais, Centavos, Tipo)
            gap_cif_reais = 3 # Gap between R$ and Reais
            gap_cent_tipo = 8 # Gap between Centavos and Tipo
            
            total_price_components_width = cifrao_w + gap_cif_reais + reais_w + centavos_w
            
            # Centralize the entire price block on the price bar
            r_draw_x_base = bar_pos_x + ((prbar_x_size - total_price_components_width) / 2)
            
            # Vertical alignment: center the 'reais' part vertically on the bar, then align others
            y_center_bar = bar_pos_y + (prbar_y_size / 2)
            
            # Positioning 'R$' (top-left aligned to its reference point)
            cif_x = r_draw_x_base
            cif_y = y_center_bar - (reais_h / 2) # Align 'R$' top with top of reais
            draw.text((cif_x, cif_y), cifrao_str, font=fonts['price_unit'], anchor="lt", fill=price_font_color)
            cif_final_pos = (cif_x, cif_y) # Store for ST seal

            # Positioning Reais part (bottom-left aligned)
            reais_x = cif_x + cifrao_w + gap_cif_reais
            reais_y = y_center_bar + (reais_h / 2) # Align reais baseline with y_center_bar
            draw.text((reais_x, reais_y), reais_part, font=fonts['price_real'], anchor="ls", fill=price_font_color)
            
            # Positioning Centavos part (bottom-left aligned, adjusted to align with reais top/cap height)
            centavos_x = reais_x + reais_w
            centavos_y = y_center_bar + (reais_h / 2) - (reais_h - centavos_h) # Adjust baseline of cents to align with top of reals
            draw.text((centavos_x, centavos_y), centavos_part_val, font=fonts['price_cent'], anchor="lb", fill=price_font_color)
            
            # Positioning Tipo/Unit (top-left aligned)
            if tip_val_rendered:
                tip_x = centavos_x + (centavos_w/4)
                tip_y = y_center_bar + (reais_h / 2) # Align tip top with reais top
                draw.text((tip_x, tip_y), tip_val_rendered, font=fonts['price_unit'], anchor="lb", fill=price_font_color)
        else:
            # Percentage price
            pct_font_color = font_configs['percentage']['color']

            preco_pct_val = round(preco_val_float * 100)
            val_pct_str = str(int(preco_pct_val)) + '%'
            txt_desconto_str = "DE DESCONTO"
            
            prbar_center_y = bar_pos_y + (prbar_y_size / 2) + 18
            prbar_center_x = bar_pos_x + (prbar_x_size / 2) - 5
            
            # Draw percentage value (middle-bottom aligned)
            draw.text((prbar_center_x, prbar_center_y - 2), val_pct_str, 
                     font=fonts['percentage_value'], anchor="mb", fill=pct_font_color)
            
            # Draw "DE DESCONTO" (middle-top aligned)
            draw.text((prbar_center_x, prbar_center_y + 2), txt_desconto_str, 
                     font=fonts['percentage_desc'], anchor="mt", fill=pct_font_color)
            
            if tipo:
                tip_val_rendered = str(tipo).upper()
                # Get bbox for "DE DESCONTO" to position 'tipo' relative to it
                txt_desc_bbox = draw.textbbox((0,0), txt_desconto_str, font=fonts['percentage_desc'], anchor="mt")
                txt_desc_width = txt_desc_bbox[2] - txt_desc_bbox[0]

                # Position 'tipo' to the right of "DE DESCONTO"
                tip_x_pos = prbar_center_x + (txt_desc_width / 2) + 5
                
                # Align 'tipo' vertically with "DE DESCONTO" baseline or top
                tip_y_pos = prbar_center_y + 2 # Align top of tip with top of "DE DESCONTO" text
                
                draw.text((tip_x_pos, tip_y_pos), tip_val_rendered, 
                         font=fonts['percentage_unit'], anchor="lt", fill=pct_font_color)

        return cif_final_pos # type: ignore
    

    def _add_observations(self, final_layout: Image.Image, draw: ImageDraw.ImageDraw, obs_text: str, selo: str, 
                          is_destaque: bool, bar_pos_x: int, prbar_x_size: int, obs_bar_img_pil: Image.Image, 
                          font: ImageFont.FreeTypeFont, color: tuple):
        """Adiciona barras de observação com texto ao layout."""
        obs_list = []
        if obs_text and not pd.isna(obs_text): 
            obs_list.append(str(obs_text))
        if selo and "exclusivo no site" in str(selo).lower(): 
            obs_list.append("exclusivo no site")
        
        if not obs_list: return # No observations to add

        num_obs = len(obs_list)
        obs_bar_x, obs_bar_y = obs_bar_img_pil.size

        # Spacing between bars
        obs_bar_spacing = 3

        # Total width occupied by the group of bars
        total_width = (num_obs * obs_bar_x) + ((num_obs - 1) * obs_bar_spacing)

        # Calculate horizontal center for the group of bars
        if is_destaque:
            center_x = bar_pos_x + prbar_x_size - (total_width // 2) + 10
            obs_bar_pos_y = 110 # Fixed Y for destaque
        else:
            center_x = (final_layout.width // 2) + (final_layout.width // 4) - 5 # ~3/4 width
            obs_bar_pos_y = final_layout.height - obs_bar_y - 60

        # Calculate starting X position for the first bar to center the group
        start_x = center_x - (total_width // 2)

        for idx, obs_text_item in enumerate(obs_list):
            try:
                obs_bar_pos_x = start_x + idx * (obs_bar_x + obs_bar_spacing)

                # Paste bar image
                final_layout.paste(obs_bar_img_pil, (obs_bar_pos_x, obs_bar_pos_y), mask=obs_bar_img_pil)

                # Calculate text position (centered within the bar)
                obs_text_x = obs_bar_pos_x + (obs_bar_x // 2)
                obs_text_y = obs_bar_pos_y + (obs_bar_y // 2)

                # Line break text
                lines_broken = self.linebk_pixels(obs_text_item, prbar_x_size, font, tolerancia_pixels=0)
                
                # Calculate vertical position for multi-line text
                line_gap_obs = 2
                line_count = len(lines_broken)
                
                # getbbox for 'A' returns (left, top, right, bottom), so height is bottom-top
                # Use font.getbbox("A")[3] - font.getbbox("A")[1] for robust height
                if line_count > 0:
                    font_height = font.getbbox(lines_broken[0])[3] - font.getbbox(lines_broken[0])[1] # Height of one line
                    total_text_height = (font_height * line_count) + (line_gap_obs * (line_count - 1))
                    
                    current_y_offset = -total_text_height // 2 # Start from center, go up half total height
                    
                    for line in lines_broken:
                        draw.text((obs_text_x, obs_text_y + current_y_offset), line, font=font, fill=color, anchor="mm")
                        current_y_offset += (font_height + line_gap_obs)
                
                self._dprint(f"     Barra de observação adicionada com texto: '{obs_text_item}'.", level=3)

            except Exception as e:
                self._dprint(f"!!! Erro ao adicionar barra de observação: {e}", level=1, file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

    def close_ftp_connection(self):
        """Fecha a conexão FTP se estiver aberta."""
        if self.ftp_conn:
            try:
                self.ftp_conn.quit()
                self._dprint("Conexão FTP desconectada.", level=3)
            except Exception as e:
                self._dprint(f"Erro ao fechar conexão FTP: {e}", level=1, file=sys.stderr)
            finally:
                self.ftp_conn = None

    def cleanup_temp_dir(self):
        """Remove o diretório temporário local."""
        if self.LOCAL_TEMP_PROCESSING_DIR.exists():
            try:
                rmtree(self.LOCAL_TEMP_PROCESSING_DIR)
                self._dprint(f"Diretório temporário '{self.LOCAL_TEMP_PROCESSING_DIR}' removido.", level=2)
            except Exception as e:
                self._dprint(f"Erro ao limpar diretório temporário '{self.LOCAL_TEMP_PROCESSING_DIR}': {e}", level=1, file=sys.stderr)
    
    def set_font_size(self, texto:str, main_size:list, fonte_path):
        largura_max = main_size[0]
        altura_max = main_size[1]
        tamanho = 1

        while True:
            fonte = ImageFont.truetype(fonte_path, tamanho)
            # cria imagem temporária só para medir
            img = Image.new("RGB", (largura_max, altura_max))
            draw = ImageDraw.Draw(img)
            bbox = draw.textbbox((0, 0), texto, font=fonte)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

            if text_w > largura_max or text_h > altura_max:
                return tamanho - 1  # último válido
            tamanho += 1

# Exemplo de uso da classe (similar ao __main__ original, mas chamando a classe)
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Processa produtos para gerar layouts de imagem.")
    parser.add_argument('--prod-code', type=int, required=True, help="Código do produto.")
    parser.add_argument('--preco', type=str, required=True, help="Preço do produto (ex: 'R$12,99' ou '0.15').")
    parser.add_argument('--descricao', type=str, required=True, help="Descrição do produto.")
    parser.add_argument('--client', type=str, default="dellys", choices=["dellys", "ns"], help="Cliente (dellys ou ns).")
    parser.add_argument('--obs', type=str, default=None, help="Observação opcional.")
    parser.add_argument('--tipo', type=str, default=None, help="Tipo/unidade do produto (ex: 'KG', 'UN').")
    parser.add_argument('--selo', type=str, default=None, help="Selos do produto (ex: 'ME, ST').")
    parser.add_argument('--output-dir', type=Path, default=Path("./output_layouts"), 
                        help="Diretório de saída para o layout.")
    parser.add_argument('--preset', type=str, required=True, 
                        help="Nome da pasta do preset (ex: inverno, junino) em xlsx_code/presets/.")
    parser.add_argument('--is-destaque', action='store_true', help="Marcar como produto de destaque.")
    parser.add_argument('--force-recreate', action='store_true', help="Forçar recriação do layout.")
    parser.add_argument('--debug', type=int, default=1, choices=[0,1,2,3], help="Nível de debug (0-3).")
    
    args = parser.parse_args()

    processor = None
    
    try:
        processor = XlsxLayoutProcessor(preset_name=args.preset,
                                        FTP_HOST="177.154.191.246", FTP_USER="dellysns@rgconsultorias.com.br", FTP_PASS="&FlgBe59XHqw",
                                        debug_level=args.debug)
        
        # Make sure the output directory exists
        args.output_dir.mkdir(parents=True, exist_ok=True)

        layout_obj = processor.process_product(
            prod_code=args.prod_code,
            preco=args.preco,
            descricao=args.descricao,
            client=args.client,
            obs=args.obs,
            tipo=args.tipo,
            selo=args.selo,
            output_dir=args.output_dir,
            is_destaque=args.is_destaque,
            force_recreate=args.force_recreate
        )

        if layout_obj:
            print(f"Layout gerado com sucesso: {Path(layout_obj).resolve()}")
        else:
            print("Falha ao gerar o layout.", file=sys.stderr)
            sys.exit(1)

    except FileNotFoundError as fnfe:
        print(f"ERRO: {fnfe}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERRO inesperado: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    finally:
        if processor:
            processor.close_ftp_connection()
            processor.cleanup_temp_dir()
        print("\nScript Concluído (execução via __main__).\n")