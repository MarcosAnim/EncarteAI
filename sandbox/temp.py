from PIL import Image

def duplicar_produto_atras(
    imagem,
    saida=None,
    proporcao=1.25,          # só aplica se altura/largura >= proporcao
    escala_fundo=0.90,        # escala da cópia de trás
    deslocamento=(230, 0),    # quanto a frente desce/direita (ou o quanto o fundo aparece no topo/esquerda)
    opacidade_fundo=0.95,     # 0..1 (deixa o fundo um tiquinho mais “atrás”)
    cor_canvas=(255, 255, 255, 0),  # RGBA; 0 = transparente
    sempre_aplicar=False,
    manter_tamanho=False      # se True, mantém tamanho final = original (reduzindo a frente se precisar)
):
    """
    imagem: str (caminho) ou PIL.Image.Image
    saida: caminho opcional para salvar
    Retorna: PIL.Image.Image do resultado
    """
    # Abre imagem (força RGBA para respeitar transparência)
    if isinstance(imagem, Image.Image):
        img = imagem.convert("RGBA")
    else:
        img = Image.open(imagem).convert("RGBA")

    w, h = img.size
    vertical_o_suficiente = (h / w) >= proporcao

    if not (vertical_o_suficiente or sempre_aplicar):
        # Não aplica o efeito; apenas salva/retorna original
        if saida:
            img.save(saida)
        return img

    # Prepara a cópia do fundo (menor)
    fundo = img.resize((int(w * escala_fundo), int(h * escala_fundo)), Image.LANCZOS)

    if opacidade_fundo < 1:
        alpha = fundo.split()[-1]
        alpha = alpha.point(lambda a: int(a * opacidade_fundo))
        fundo.putalpha(alpha)

    dx, dy = deslocamento

    if manter_tamanho:
        # Mantém o tamanho final = (w, h).
        # Para o fundo aparecer sem cortar a frente, reduzimos um pouco a frente se necessário.
        esc_frente = min(1.0, (w - dx) / w, (h - dy) / h)
        frente = img if esc_frente >= 1 else img.resize((int(w * esc_frente), int(h * esc_frente)), Image.LANCZOS)

        canvas = Image.new("RGBA", (w, h), cor_canvas)
        # cola o fundo no canto superior/esquerdo
        canvas.paste(fundo, (0, 0), fundo)
        # cola a frente deslocada (para o fundo “aparecer” atrás, no topo/esquerda)
        canvas.paste(frente, (dx, dy), frente)
    else:
        # Expande o canvas para garantir que o fundo apareça mesmo com frente opaca
        cw = max(w + dx, fundo.size[0])
        ch = max(h + dy, fundo.size[1])
        canvas = Image.new("RGBA", (cw, ch), cor_canvas)
        # fundo visível no topo/esquerda
        canvas.paste(fundo, (0, 0), fundo)
        # frente deslocada para baixo/direita
        canvas.paste(img, (dx, dy), img)

    if saida:
        canvas.save(saida)

    return canvas


duplicar_produto_atras(r"C:\Users\Marcos\Downloads\98251.png", r"C:\Users\Marcos\Downloads\98251-test.png")