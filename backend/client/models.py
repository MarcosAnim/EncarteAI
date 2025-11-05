from dataclasses import dataclass
import os

@dataclass
class GeneratedLayout:
    """
    Representa o resultado de uma geração de layout bem-sucedida.
    Contém os dados binários da imagem e metadados associados.
    """
    image_data: bytes
    filename: str
    content_type: str
    source_request: str 

    def save(self, output_dir: str = ".", overwrite: bool = True) -> str:
        """
        Salva os dados binários da imagem em um arquivo.

        Args:
            output_dir (str): O diretório onde a imagem será salva. O padrão é o diretório atual.
            overwrite (bool): Se True, sobrescreve o arquivo se ele já existir.

        Returns:
            str: O caminho completo do arquivo salvo.
        """
        # Garante que o diretório de saída exista
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, self.filename)

        if not overwrite and os.path.exists(file_path):
            print(f"Arquivo '{file_path}' já existe e 'overwrite' é False. Pulando salvamento.")
            return file_path

        with open(file_path, "wb") as f:
            f.write(self.image_data)
        
        print(f"Imagem salva com sucesso em: {file_path}")
        return file_path