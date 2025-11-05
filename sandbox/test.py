import sys
from pathlib import Path
import subprocess
import os
import time  # Importa o módulo time
# python E:\Files\Trabalho\PrimeiroNegócio\live_viewer.py E:\Files\Trabalho\PrimeiroNegócio\CodeXlsxGen\xlsx_code\presets\output_layouts\testsheet\NS\116768.png
base_dir = Path(__file__).parent  # Diretório base do código
target_file = r'E:\Files\Trabalho\PrimeiroNegócio\CodeXlsxGen\xlsx_code\presets\output_layouts\testsheet\NS\116768.png'
script_full_path = base_dir / 'XlsxGen_LayoutProcessor.py'
script_full_path_html = base_dir / 'HTMLGen.py'
script_layout_output_dir = 'C:/Users/Marcos/Desktop/Output'  # Diretório de saída para layouts
selected_preset = base_dir / 'presets' / 'Aniversario'
trigg = 1  # 1 para layout, 2 para HTML

if trigg == 1:
    command = [
        sys.executable, str(script_full_path),
        '--input-excel', str((base_dir / 'presets' / 'output_layouts' / 'NS.xlsx').resolve()),
        '--output-layout-dir', str((base_dir / 'presets' / 'output_layouts' / 'testsheet').resolve()),
        '--preset', selected_preset,  # Preset selecionado pelo usuário
        '--debug', '1'  # Ajuste o nível de debug conforme necessário
    ]

elif trigg==2:
    command = [
        sys.executable, str(script_full_path_html),
        '--input-excel', str((base_dir / 'presets' / 'output_layouts' / 'NS.xlsx').resolve()),
        '--zip-images-path', str((base_dir / 'presets' / 'output_layouts' / 'testsheet').resolve()),
        '--output-html-dir', str((base_dir / 'presets' / 'output_layouts').resolve()),
        '--date-ref-ftp', '0000-00-00',
        '--texto-validade', '00-00-00 até 00/00/00',
        '--preset', selected_preset,
        '--debug', '1'
    ]

while True:
    if os.path.exists(target_file):
        os.remove(target_file)
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        print(result.stdout)
        print(result.stderr)
    except:
        print('Main code in edition')
    
    time.sleep(0.5)
    
    