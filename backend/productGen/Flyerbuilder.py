import json
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
import math

# ---------------------------------------------
# CLASSE CELL (Atualizada para transparência padrão)
# ---------------------------------------------

class Cell:
    DEFAULT_CONFIG = {
        "id": None, "row": 0, "col": 0, "rowspan": 1, "colspan": 1,
        # Fundo da célula agora é totalmente transparente (Alpha 0)
        "color": [220, 220, 220, 0], 
        "text": None, "text_color": [0, 0, 0, 255], "font_size": 60,
        "image_path": None,
        "preserve_aspect_ratio": True, 
        "fit_mode": "contain",         
        "padding": 0, 
        "align_horizontal": "center", "align_vertical": "center",
        # Outline da célula agora é totalmente transparente (Alpha 0)
        "outline_color": [64, 64, 64, 0]
    }

    def __init__(self, config: dict):
        self.config = self.DEFAULT_CONFIG.copy()
        self.config.update(config)

        # Mapeamento de atributos
        self.id = self.config['id']
        self.row = self.config['row']
        self.col = self.config['col']
        self.rowspan = self.config['rowspan']
        self.colspan = self.config['colspan']

        # Cores (Garantir tuplas RGBA)
        self.color = tuple(self.config['color']) if isinstance(self.config['color'], list) else self.config['color']
        self.outline_color = tuple(self.config['outline_color']) if isinstance(self.config['outline_color'], list) else self.config['outline_color']
        self.text_color = tuple(self.config['text_color']) if isinstance(self.config['text_color'], list) else self.config['text_color']

        # Conteúdo
        self.text = self.config['text']
        self.font_size = self.config['font_size']
        self.padding = self.config['padding']
        self.align_horizontal = self.config['align_horizontal']
        self.align_vertical = self.config['align_vertical']
        
        # Propriedades de Imagem
        self.image_path = self.config['image_path']
        self.preserve_aspect_ratio = self.config['preserve_aspect_ratio']
        self.fit_mode = self.config['fit_mode']


        # Fonte (Carregamento simples)
        try:
            self.font = ImageFont.truetype("arial.ttf", self.font_size)
        except Exception:
            self.font = ImageFont.load_default()
            
        self.image = None
        if self.image_path:
            try:  
                # Carrega a imagem e garante o canal RGBA para transparência
                self.image = Image.open(self.image_path).convert("RGBA")
            except Exception as e:
                print(f"Erro ao carregar imagem {self.image_path}: {e}")
                pass

    def _resize_image_with_aspect_ratio(self, image, max_width, max_height):
        """Implementação da lógica de redimensionamento 'contain' ou 'cover'."""
        original_width, original_height = image.size
        aspect_ratio = original_width / original_height
        
        if self.fit_mode == "contain":
            if max_width / max_height > aspect_ratio:
                new_height = max_height
                new_width = int(new_height * aspect_ratio)
            else:
                new_width = max_width
                new_height = int(new_width / aspect_ratio)
        else: # "cover"
            if max_width / max_height > aspect_ratio:
                new_width = max_width
                new_height = int(new_width / aspect_ratio)
            else:
                new_height = max_height
                new_width = int(new_height * aspect_ratio)
                
        new_width = max(1, new_width)
        new_height = max(1, new_height)
                
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def draw(self, draw, x, y, width, height, border_width):
        """Desenha a célula e seu conteúdo no espaço alocado."""
        
        parent_img = draw._image # Acesso ao objeto Image da PIL
        
        # 1. Desenha o fundo e a borda da célula
        # Se self.color e self.outline_color tiverem Alpha=0, eles serão transparentes
        draw.rectangle([x, y, x + width, y + height], 
                       fill=self.color, 
                       outline=self.outline_color, 
                       width=border_width)

        inner_x = x + self.padding
        inner_y = y + self.padding
        inner_w = width - 2 * self.padding
        inner_h = height - 2 * self.padding

        # 2. Desenha a Imagem
        if self.image and inner_w > 0 and inner_h > 0:
            
            if self.preserve_aspect_ratio:
                resized_image = self._resize_image_with_aspect_ratio(self.image, inner_w, inner_h)
            else:
                resized_image = self.image.resize((int(inner_w), int(inner_h)), Image.Resampling.LANCZOS)
            
            img_width, img_height = resized_image.size
            
            # Cálculo de offset para centralização/alinhamento da imagem
            x_offset = 0
            y_offset = 0
            
            if self.align_horizontal == "center":
                x_offset = (inner_w - img_width) // 2
            elif self.align_horizontal == "right":
                x_offset = inner_w - img_width
                
            if self.align_vertical == "center":
                y_offset = (inner_h - img_height) // 2
            elif self.align_vertical == "bottom":
                y_offset = inner_h - img_height
                
            x_paste = int(inner_x + x_offset)
            y_paste = int(inner_y + y_offset)

            # Colagem da imagem (usando a própria imagem como máscara para lidar com transparência)
            parent_img.paste(resized_image, (x_paste, y_paste), resized_image)


        # 3. Desenha o Texto
        text_content = self.text if self.text is not None else self.id
        
        if text_content:
            
            bbox = draw.textbbox((0, 0), text_content, font=self.font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            # Alinhamento horizontal do texto
            if self.align_horizontal == "center":
                text_x = inner_x + (inner_w - text_w) // 2
            elif self.align_horizontal == "left":
                text_x = inner_x
            else:
                text_x = inner_x + inner_w - text_w
                
            # Alinhamento vertical do texto
            if self.align_vertical == "center":
                text_y = inner_y + (inner_h - text_h) // 2
            elif self.align_vertical == "top":
                text_y = inner_y
            else:
                text_y = inner_y + inner_h - text_h
            
            draw.text((text_x, text_y), text_content, fill=self.text_color, font=self.font)


# ---------------------------------------------
# CLASSE GRIDCONTAINER (Atualizada para RGBA)
# ---------------------------------------------

class GridContainer:
    def __init__(self, cell_size=200, border_width=8, bg_color="#DCDCDC00", 
                 border_color="#40404000", canvas_color="#50505000"):
        
        self.cell_size = cell_size
        self.border_width = border_width
        
        # Usa a nova função que suporta 8 dígitos hex (RGBA)
        self.bg_color = self._hex_to_rgba(bg_color)
        self.border_color = self._hex_to_rgba(border_color)
        self.canvas_color = self._hex_to_rgba(canvas_color)
        
        self.rows = 0
        self.cols = 0
        self.cells = []
        self.img = None

    # NOVO: Função que suporta conversão de Hex (6 ou 8 dígitos) para RGBA (4 valores)
    def _hex_to_rgba(self, hex_color):
        if isinstance(hex_color, str) and hex_color.startswith('#'):
            hex_color = hex_color.lstrip('#')
            
            if len(hex_color) == 6:
                # RGB, assume Alpha 255 (opaco)
                rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                return rgb + (255,)
            
            elif len(hex_color) == 8:
                # RGBA
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4, 6))

        if isinstance(hex_color, (list, tuple)):
            if len(hex_color) == 3:
                return hex_color + (255,) # Se for RGB, torna opaco
            return hex_color
            
        return hex_color


    def create_from_json(self, data):
        if isinstance(data, str):
            data = json.loads(data)
        
        self.rows = data['rows']
        self.cols = data['cols']
        self.cells = []
        
        for cell_data in data['cells']:
            # Se a cor não for definida, usará o self.bg_color (que já pode ser transparente)
            if 'color' not in cell_data or cell_data['color'] is None:
                cell_data['color'] = self.bg_color
            
            if 'outline_color' not in cell_data:
                cell_data['outline_color'] = self.border_color
                
            self.cells.append(Cell(cell_data))
        
        self._render_image()
    
    def _render_image(self):
        
        if self.rows == 0 or self.cols == 0:
            return 
            
        width = self.cols * self.cell_size + (self.cols + 1) * self.border_width
        height = self.rows * self.cell_size + (self.rows + 1) * self.border_width
        
        # Cria imagem usando RGBA. O self.canvas_color (que foi definido como #50505000) 
        # agora garante que o fundo da imagem seja totalmente transparente.
        self.img = Image.new('RGBA', (width, height), self.canvas_color) 
        draw = ImageDraw.Draw(self.img)
        draw._image = self.img 

        
        for cell in self.cells:
            x_start = cell.col * (self.cell_size + self.border_width) + self.border_width
            y_start = cell.row * (self.cell_size + self.border_width) + self.border_width
            
            w = cell.colspan * self.cell_size + (cell.colspan - 1) * self.border_width
            h = cell.rowspan * self.cell_size + (cell.rowspan - 1) * self.border_width
            
            cell.draw(draw, x_start, y_start, w, h, self.border_width)
            
    
    def save(self, output_path='grid_output.png'):
        if self.img is None: self._render_image()
        # Salvar como PNG é essencial, pois JPG não suporta transparência.
        self.img.save(output_path) 
        print(f"Imagem salva em: {output_path}")

    def show(self):
        if self.img is None: self._render_image()
        self.img.show()


# Exemplo de uso
if __name__ == "__main__":
    
    # -----------------------------------------------------
    # Exemplo 2 Modificado:
    # O GridContainer já está sendo inicializado com:
    # bg_color="#DCDCDC00" (Fundo padrão da célula: transparente)
    # border_color="#40404000" (Bordas do grid: transparente)
    # canvas_color="#50505000" (Fundo total da imagem: transparente)
    # -----------------------------------------------------
    
    IMAGE_PATH = "C:/Users/Marcos/Documents/Projetosgit/EncarteAi/15.png"
    
    if not os.path.exists(IMAGE_PATH):
        print(f"ATENÇÃO: A imagem não foi encontrada em {IMAGE_PATH}.")

    grid_data2_with_image = {
        "rows": 3,
        "cols": 3,
        "cells": [

            {"id": "A1", "row": 0, "col": 0, "rowspan": 2, "colspan": 2, 
             "image_path": IMAGE_PATH,"font_size": 30,"padding": 10,
             "preserve_aspect_ratio": True,"fit_mode": "contain"},
                 
            {"id": "C1", "row": 0, "col": 2, "color": [255, 0, 0, 50]},
            
            {"id": "C2", "row": 1, "col": 2, "color": [0, 255, 0, 50]},

            {"id": "A3", "row": 2, "col": 0, "color": [0, 255, 0, 50]},
            
            {"id": "B3", "row": 2, "col": 1, "rowspan": 1, "colspan": 2,"color": [0, 255, 0, 50]}
        ]
    }
    
    # GridContainer com Fundo/Borda do Canvas transparente (padrão)
    grid2 = GridContainer(cell_size=200) 
    grid2.create_from_json(grid_data2_with_image)
    grid2.save('grid_exemplo_transparente.png')
    grid2.show()