import pandas as pd
import json
import tempfile
import os
from typing import Dict, List, Optional, Union
#from pathlib import Path
import shutil


class XLSXToJSONReader:
    """
    Classe para ler planilhas XLSX e criar um diretório temporário em memória 
    com os dados convertidos para arquivos JSON.
    """
    
    def __init__(self, xlsx_file_path: str):
        """
        Inicializa a classe com o caminho do arquivo XLSX.
        
        Args:
            xlsx_file_path (str): Caminho para o arquivo XLSX
        """
        self.xlsx_file_path = xlsx_file_path
        self.temp_dir = None
        self.data = {}
        self.sheet_names = []
        
    def read_xlsx(self, sheet_name: Optional[Union[str, List[str]]] = None) -> Dict:
        """
        Lê o arquivo XLSX e armazena os dados em memória.
        
        Args:
            sheet_name: Nome da planilha específica ou lista de nomes. 
                       Se None, lê todas as planilhas.
        
        Returns:
            Dict: Dados das planilhas organizados por nome da planilha
        """
        try:
            # Lê todas as planilhas ou planilhas específicas
            if sheet_name is None:
                # Lê todas as planilhas
                excel_data = pd.read_excel(self.xlsx_file_path, sheet_name=None)
                self.data = excel_data
                self.sheet_names = list(excel_data.keys())
            else:
                # Lê planilhas específicas
                excel_data = pd.read_excel(self.xlsx_file_path, sheet_name=sheet_name)
                
                if isinstance(sheet_name, str):
                    self.data = {sheet_name: excel_data}
                    self.sheet_names = [sheet_name]
                else:
                    self.data = excel_data
                    self.sheet_names = list(excel_data.keys())
            
            print(f"✅ Arquivo XLSX lido com sucesso!")
            print(f"📊 Planilhas encontradas: {self.sheet_names}")
            return self.data # type: ignore
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Arquivo não encontrado: {self.xlsx_file_path}")
        except Exception as e:
            raise Exception(f"Erro ao ler arquivo XLSX: {str(e)}")
    
    def create_temp_directory(self) -> str:
        """
        Cria um diretório temporário para armazenar os arquivos JSON.
        
        Returns:
            str: Caminho do diretório temporário criado
        """
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="xlsx_json_")
            print(f"📁 Diretório temporário criado: {self.temp_dir}")
            return self.temp_dir
        except Exception as e:
            raise Exception(f"Erro ao criar diretório temporário: {str(e)}")
    
    def convert_to_json_files(self, 
                             orient: str = 'records',
                             date_format: str = 'iso',
                             indent: int = 2) -> Dict[str, str]:
        """
        Converte os dados das planilhas para arquivos JSON no diretório temporário.
        
        Args:
            orient (str): Formato de orientação do JSON ('records', 'index', 'values', etc.)
            date_format (str): Formato das datas ('iso', 'epoch')
            indent (int): Indentação do JSON para formatação
        
        Returns:
            Dict[str, str]: Dicionário com nome da planilha e caminho do arquivo JSON
        """
        if not self.data: # type: ignore
            raise ValueError("Nenhum dado carregado. Execute read_xlsx() primeiro.")
        
        if not self.temp_dir:
            self.create_temp_directory()
        
        json_files = {}
        
        try:
            for sheet_name, df in self.data.items():
                # Nome do arquivo JSON
                json_filename = f"{sheet_name}.json"
                json_path = os.path.join(self.temp_dir, json_filename)# type: ignore
                
                # Converte DataFrame para JSON
                json_data = df.to_json( orient=orient, date_format=date_format, force_ascii=False) # type: ignore
                
                # Parse para formatar corretamente
                parsed_data = json.loads(json_data)
                
                # Salva arquivo JSON formatado
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(parsed_data, f, indent=indent, ensure_ascii=False)
                
                json_files[sheet_name] = json_path
                print(f"📄 JSON criado: {json_filename}")
            
            print(f"✅ {len(json_files)} arquivo(s) JSON criado(s) com sucesso!")
            return json_files
            
        except Exception as e:
            raise Exception(f"Erro ao converter para JSON: {str(e)}")
    
    def get_data_summary(self) -> Dict:
        """
        Retorna um resumo dos dados carregados.
        
        Returns:
            Dict: Resumo com informações sobre as planilhas
        """
        if not self.data:# type: ignore
            return {"message": "Nenhum dado carregado"}
        
        summary = {}
        for sheet_name, df in self.data.items():
            summary[sheet_name] = {
                "linhas": len(df),
                "colunas": len(df.columns),# type: ignore
                "colunas_nomes": list(df.columns),# type: ignore
                "tipos_dados": df.dtypes.to_dict() # type: ignore
            }
        
        return summary
    
    def list_json_files(self) -> List[str]:
        """
        Lista os arquivos JSON criados no diretório temporário.
        
        Returns:
            List[str]: Lista com os caminhos dos arquivos JSON
        """
        if not self.temp_dir or not os.path.exists(self.temp_dir):
            return []
        
        json_files = []
        for file in os.listdir(self.temp_dir):
            if file.endswith('.json'):
                json_files.append(os.path.join(self.temp_dir, file))
        
        return json_files
    
    def read_json_file(self, sheet_name: str) -> Dict:
        """
        Lê um arquivo JSON específico do diretório temporário.
        
        Args:
            sheet_name (str): Nome da planilha/arquivo JSON
            
        Returns:
            Dict: Dados do arquivo JSON
        """
        if not self.temp_dir:
            raise ValueError("Diretório temporário não foi criado")
        
        json_path = os.path.join(self.temp_dir, f"{sheet_name}.json")
        
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Arquivo JSON não encontrado: {json_path}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Erro ao ler arquivo JSON: {str(e)}")
    
    def cleanup(self):
        """
        Remove o diretório temporário e todos os arquivos.
        """
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                print(f"🗑️ Diretório temporário removido: {self.temp_dir}")
                self.temp_dir = None
            except Exception as e:
                print(f"⚠️ Erro ao remover diretório temporário: {str(e)}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - limpa recursos automaticamente."""
        self.cleanup()


# Exemplo de uso
if __name__ == "__main__":
    # Exemplo de uso da classe
    xlsx_file = r"E:\Files\Trabalho\Fastlay\CodeXlsxGen\xlsx_code\presets\output_layouts\NS.xlsx"  # substitua pelo caminho do seu arquivo
    
    try:
        # Usando context manager para limpeza automática
        with XLSXToJSONReader(xlsx_file) as reader:
            # Lê o arquivo XLSX
            data = reader.read_xlsx()
            
            # Mostra resumo dos dados
            summary = reader.get_data_summary()
            print("\n📊 Resumo dos dados:")
            for sheet, info in summary.items():
                print(f"  {sheet}: {info['linhas']} linhas, {info['colunas']} colunas")
            
            # Converte para arquivos JSON
            json_files = reader.convert_to_json_files()
            
            # Lista arquivos criados
            print(f"\n📁 Diretório temporário: {reader.temp_dir}")
            print("📄 Arquivos JSON criados:")
            for sheet, path in json_files.items():
                print(f"  {sheet}: {path}")
            
            # Exemplo de leitura de um arquivo JSON específico
            if json_files:
                first_sheet = list(json_files.keys())[0]
                json_data = reader.read_json_file(first_sheet)
                print(f"\n📖 Primeiros registros de '{first_sheet}':")
                if isinstance(json_data, list) and len(json_data) > 0:
                    print(json.dumps(json_data[:2], indent=2, ensure_ascii=False))
        
        print("\n✅ Processamento concluído e recursos limpos automaticamente!")
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")