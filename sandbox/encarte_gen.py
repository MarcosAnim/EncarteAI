from PIL import Image
import os
import logging
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FitMode(Enum):
    """Modos de ajuste das imagens nos slots"""
    CONTAIN = "contain"  # Mantém proporção, cabe totalmente no slot
    COVER = "cover"      # Mantém proporção, preenche o slot (pode cortar)
    STRETCH = "stretch"  # Estica para preencher o slot (pode distorcer)

class AlignmentMode(Enum):
    """Modos de alinhamento das imagens nos slots"""
    CENTER = "center"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    TOP_CENTER = "top_center"
    BOTTOM_CENTER = "bottom_center"
    CENTER_LEFT = "center_left"
    CENTER_RIGHT = "center_right"

@dataclass
class LayoutConfig:
    """Configurações para o layout de imagens"""
    images_per_row: Optional[int] = None
    padding_horizontal: int = 10
    padding_vertical: int = 10
    padding_border: int = 10
    fit_mode: FitMode = FitMode.CONTAIN
    alignment: AlignmentMode = AlignmentMode.CENTER
    green_threshold: int = 80
    remove_green_pixels: bool = True
    green_replacement_color: Optional[Tuple[int, int, int]] = None
    min_slot_size: int = 50
    max_slot_size: Optional[int] = None
    preserve_aspect_ratio: bool = True
    background_color: Tuple[int, int, int] = (255, 255, 255)
    quality: int = 95

class ImageLayoutProcessor:
    """Processador robusto para layout de imagens com área verde delimitadora"""
    
    def __init__(self, config: LayoutConfig = None):
        self.config = config or LayoutConfig()
        
    def find_green_bounding_box(self, image_path: str, green_color: Tuple[int, int, int] = (0, 255, 0)) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
        """
        Encontra o bounding box de todos os pixels verdes em uma imagem.
        
        Args:
            image_path: Caminho para a imagem
            green_color: Cor verde de referência (R, G, B)
            
        Returns:
            Tuple com (min_x, min_y, max_x, max_y) ou (None, None, None, None) se não encontrar verde
        """
        try:
            img = Image.open(image_path).convert('RGB')
        except Exception as e:
            logger.error(f"Erro ao carregar imagem de background {image_path}: {e}")
            return None, None, None, None

        pixels = img.load()
        width, height = img.size

        min_x, min_y = width, height
        max_x, max_y = -1, -1
        found_green = False

        for y in range(height):
            for x in range(width):
                if self._is_green_pixel(pixels[x, y], green_color):
                    found_green = True
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        if found_green:
            logger.info(f"Área verde encontrada: ({min_x}, {min_y}) a ({max_x}, {max_y})")
            return min_x, min_y, max_x, max_y
        else:
            logger.warning("Nenhum pixel verde encontrado na imagem de background")
            return None, None, None, None

    def _is_green_pixel(self, pixel: Tuple[int, int, int], green_ref: Tuple[int, int, int]) -> bool:
        """Verifica se um pixel é verde dentro da tolerância configurada"""
        if len(pixel) != 3:
            return False
        
        r, g, b = pixel
        ref_r, ref_g, ref_b = green_ref
        
        # Distância euclidiana
        distance = ((r - ref_r) ** 2 + (g - ref_g) ** 2 + (b - ref_b) ** 2) ** 0.5
        return distance < self.config.green_threshold

    def _calculate_optimal_grid(self, n_images: int, area_width: int, area_height: int) -> int:
        """
        Calcula o número ideal de imagens por linha baseado na área disponível.
        
        Args:
            n_images: Número total de imagens
            area_width: Largura da área disponível
            area_height: Altura da área disponível
            
        Returns:
            Número ideal de imagens por linha
        """
        if n_images == 0:
            return 1
            
        best_cols = 1
        min_score = float('inf')
        
        # Proporção da área disponível
        area_aspect = area_width / area_height if area_height > 0 else 1.0
        
        for cols in range(1, n_images + 1):
            rows = (n_images + cols - 1) // cols
            
            # Espaço disponível para conteúdo
            content_width = area_width - (cols + 1) * self.config.padding_horizontal
            content_height = area_height - (rows + 1) * self.config.padding_vertical
            
            if content_width <= 0 or content_height <= 0:
                continue
                
            # Tamanho médio dos slots
            slot_width = content_width / cols
            slot_height = content_height / rows
            
            if slot_width < self.config.min_slot_size or slot_height < self.config.min_slot_size:
                continue
                
            # Calcular score baseado na diferença de aspecto
            grid_aspect = (cols * slot_width) / (rows * slot_height)
            score = abs(grid_aspect - area_aspect)
            
            # Penalizar slots muito pequenos
            min_slot = min(slot_width, slot_height)
            if min_slot < self.config.min_slot_size:
                score += 1000
                
            if score < min_score:
                min_score = score
                best_cols = cols
                
        logger.info(f"Grid otimizado: {best_cols} colunas para {n_images} imagens")
        return best_cols

    def _resize_image(self, img: Image.Image, slot_width: int, slot_height: int) -> Image.Image:
        """
        Redimensiona uma imagem baseado no modo de ajuste configurado.
        
        Args:
            img: Imagem PIL
            slot_width: Largura do slot
            slot_height: Altura do slot
            
        Returns:
            Imagem redimensionada
        """
        img_width, img_height = img.size
        
        if self.config.fit_mode == FitMode.STRETCH:
            return img.resize((slot_width, slot_height), Image.Resampling.LANCZOS)
        
        elif self.config.fit_mode == FitMode.CONTAIN:
            ratio = min(slot_width / img_width, slot_height / img_height)
            new_width = max(1, int(img_width * ratio))
            new_height = max(1, int(img_height * ratio))
            return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        elif self.config.fit_mode == FitMode.COVER:
            ratio = max(slot_width / img_width, slot_height / img_height)
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)
            
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Cortar para caber no slot
            left = (new_width - slot_width) // 2
            top = (new_height - slot_height) // 2
            right = left + slot_width
            bottom = top + slot_height
            
            return resized.crop((left, top, right, bottom))
        
        return img

    def _calculate_paste_position(self, img_width: int, img_height: int, 
                                slot_x: int, slot_y: int, slot_width: int, slot_height: int) -> Tuple[int, int]:
        """
        Calcula a posição para colar a imagem baseado no alinhamento configurado.
        
        Args:
            img_width: Largura da imagem
            img_height: Altura da imagem
            slot_x: Posição X do slot
            slot_y: Posição Y do slot
            slot_width: Largura do slot
            slot_height: Altura do slot
            
        Returns:
            Tuple com (x, y) para colar a imagem
        """
        if self.config.alignment == AlignmentMode.CENTER:
            x = slot_x + (slot_width - img_width) // 2
            y = slot_y + (slot_height - img_height) // 2
        elif self.config.alignment == AlignmentMode.TOP_LEFT:
            x = slot_x
            y = slot_y
        elif self.config.alignment == AlignmentMode.TOP_RIGHT:
            x = slot_x + slot_width - img_width
            y = slot_y
        elif self.config.alignment == AlignmentMode.BOTTOM_LEFT:
            x = slot_x
            y = slot_y + slot_height - img_height
        elif self.config.alignment == AlignmentMode.BOTTOM_RIGHT:
            x = slot_x + slot_width - img_width
            y = slot_y + slot_height - img_height
        elif self.config.alignment == AlignmentMode.TOP_CENTER:
            x = slot_x + (slot_width - img_width) // 2
            y = slot_y
        elif self.config.alignment == AlignmentMode.BOTTOM_CENTER:
            x = slot_x + (slot_width - img_width) // 2
            y = slot_y + slot_height - img_height
        elif self.config.alignment == AlignmentMode.CENTER_LEFT:
            x = slot_x
            y = slot_y + (slot_height - img_height) // 2
        elif self.config.alignment == AlignmentMode.CENTER_RIGHT:
            x = slot_x + slot_width - img_width
            y = slot_y + (slot_height - img_height) // 2
        else:
            # Fallback para centro
            x = slot_x + (slot_width - img_width) // 2
            y = slot_y + (slot_height - img_height) // 2
            
        return x, y

    def _remove_green_pixels(self, img: Image.Image, min_x: int, min_y: int, 
                           max_x: int, max_y: int, green_color: Tuple[int, int, int] = (0, 255, 0)) -> None:
        """Remove pixels verdes da imagem de background"""
        if not self.config.remove_green_pixels:
            return
            
        pixels = img.load()
        replacement_color = self.config.green_replacement_color or img.getpixel((0, 0))
        
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                if self._is_green_pixel(pixels[x, y], green_color):
                    pixels[x, y] = replacement_color

    def create_layout(self, image_paths: List[str], background_path: str, 
                     output_path: str = 'layout.png') -> bool:
        """
        Cria um layout de imagens sobre um background com área verde delimitadora.
        
        Args:
            image_paths: Lista de caminhos das imagens
            background_path: Caminho da imagem de background
            output_path: Caminho para salvar o resultado
            
        Returns:
            True se bem-sucedido, False caso contrário
        """
        try:
            # Carregar background
            try:
                bg_img = Image.open(background_path).convert('RGB')
            except Exception as e:
                logger.error(f"Erro ao carregar background {background_path}: {e}")
                return False

            # Encontrar área verde
            min_x, min_y, max_x, max_y = self.find_green_bounding_box(background_path)
            
            if min_x is None:
                logger.warning("Usando toda a área do background")
                product_area = (0, 0, bg_img.width, bg_img.height)
            else:
                product_area = (min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
                self._remove_green_pixels(bg_img, min_x, min_y, max_x, max_y)

            # Carregar imagens
            images = []
            for img_path in image_paths:
                try:
                    img = Image.open(img_path)
                    if img.mode not in ('RGB', 'RGBA'):
                        img = img.convert('RGBA' if img.mode == 'P' and 'transparency' in img.info else 'RGB')
                    images.append(img)
                except Exception as e:
                    logger.warning(f"Erro ao carregar imagem {img_path}: {e}")
                    continue

            if not images:
                logger.error("Nenhuma imagem válida encontrada")
                return False

            n_images = len(images)
            area_x, area_y, area_width, area_height = product_area

            # Calcular grid
            images_per_row = self.config.images_per_row or self._calculate_optimal_grid(
                n_images, area_width, area_height)
            n_rows = (n_images + images_per_row - 1) // images_per_row

            # Calcular dimensões dos slots
            content_width = area_width - (images_per_row + 1) * self.config.padding_horizontal
            content_height = area_height - (n_rows + 1) * self.config.padding_vertical

            if content_width <= 0 or content_height <= 0:
                logger.error("Área insuficiente para layout")
                return False

            slot_width = max(self.config.min_slot_size, content_width // images_per_row)
            slot_height = max(self.config.min_slot_size, content_height // n_rows)

            if self.config.max_slot_size:
                slot_width = min(slot_width, self.config.max_slot_size)
                slot_height = min(slot_height, self.config.max_slot_size)

            # Calcular posição inicial da grade
            grid_width = images_per_row * slot_width + (images_per_row - 1) * self.config.padding_horizontal
            grid_height = n_rows * slot_height + (n_rows - 1) * self.config.padding_vertical

            start_x = area_x + (area_width - grid_width) // 2
            start_y = area_y + (area_height - grid_height) // 2

            # Posicionar imagens
            for idx, img in enumerate(images):
                row = idx // images_per_row
                col = idx % images_per_row

                slot_x = start_x + col * (slot_width + self.config.padding_horizontal)
                slot_y = start_y + row * (slot_height + self.config.padding_vertical)

                # Redimensionar imagem
                resized_img = self._resize_image(img, slot_width, slot_height)

                # Calcular posição de colagem
                paste_x, paste_y = self._calculate_paste_position(
                    resized_img.width, resized_img.height, slot_x, slot_y, slot_width, slot_height)

                # Garantir que não saia dos limites
                paste_x = max(0, min(paste_x, bg_img.width - resized_img.width))
                paste_y = max(0, min(paste_y, bg_img.height - resized_img.height))

                # Colar imagem
                mask = resized_img if resized_img.mode == 'RGBA' else None
                bg_img.paste(resized_img, (paste_x, paste_y), mask)

            # Salvar resultado
            bg_img.save(output_path, quality=self.config.quality, optimize=True)
            logger.info(f'Layout com {n_images} imagens salvo em {output_path}')
            return True

        except Exception as e:
            logger.error(f"Erro ao criar layout: {e}")
            return False

def load_images_from_directory(directory_path: str, extensions: Tuple[str, ...] = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')) -> List[str]:
    """
    Carrega lista de imagens de um diretório.
    
    Args:
        directory_path: Caminho do diretório
        extensions: Extensões de arquivo aceitas
        
    Returns:
        Lista de caminhos das imagens encontradas
    """
    image_paths = []
    
    if not os.path.exists(directory_path):
        logger.error(f"Diretório não encontrado: {directory_path}")
        return image_paths
    
    for file in os.listdir(directory_path):
        if file.lower().endswith(extensions):
            full_path = os.path.join(directory_path, file)
            image_paths.append(full_path)
    
    logger.info(f"Encontradas {len(image_paths)} imagens em {directory_path}")
    return image_paths

# Exemplo de uso
if __name__ == "__main__":
    # Configuração personalizada
    config = LayoutConfig(
        images_per_row=None,        # Cálculo automático
        padding_horizontal=1,       # Espaçamento horizontal entre imagens
        padding_vertical=1,         # Espaçamento vertical entre imagens
        padding_border=0,          # Espaçamento das bordas
        fit_mode=FitMode.CONTAIN,   # Como ajustar imagens nos slots
        alignment=AlignmentMode.CENTER,  # Alinhamento das imagens nos slots
        green_threshold=10,         # Tolerância para detectar verde
        remove_green_pixels=True,   # Remover pixels verdes do background
        min_slot_size=50,          # Tamanho mínimo dos slots
        max_slot_size=300,         # Tamanho máximo dos slots (None = sem limite)
        quality=95                 # Qualidade da imagem final (1-100)
    )
    
    # Caminhos - ajuste conforme necessário
    imgpath = r'C:\Users\Marcos\Desktop\imagens de produtos\BA'
    background_image_path = r'C:\Users\Marcos\Desktop\imagens de produtos\panfleto_teste.png'
    output_image_path = r'C:\Users\Marcos\Desktop\imagens de produtos\output.png'
    
    # Carregar imagens
    image_list = load_images_from_directory(imgpath)
    
    if image_list:
        # Criar processador e executar
        processor = ImageLayoutProcessor(config)
        success = processor.create_layout(image_list, background_image_path, output_image_path)
        
        if success:
            print("Layout criado com sucesso!")
        else:
            print("Erro ao criar layout.")
    else:
        print("Nenhuma imagem encontrada no diretório especificado.")