import os
from flask import Flask, render_template, request, send_file
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

app = Flask(__name__)

# Diretório para guardar os PDFs gerados
PDF_DIR = os.path.join(os.getcwd(), 'generated_pdfs')
os.makedirs(PDF_DIR, exist_ok=True)

# Base de dados de compatibilidade dos signos para o Mapa Astral do Casal
COMPATIBILIDADE = {
    ("Fogo", "Fogo"): dict(
        tagline="Uma explosão de paixão e entusiasmo",
        dinamica="{s1} e {s2} juntos formam uma fogueira intensa. A relação é guiada pela ação, pelo entusiasmo e por uma energia inesgotável.",
        amor="O amor é vivido de forma ardente, corajosa e direta. Não há espaço para o tédio, pois ambos adoram a conquista constante.",
        comunicacao="Direta e sem rodeios. Dizem o que pensam, o que pode gerar faíscas rápidas, mas que se dissipam com a mesma velocidade.",
        intimidade="Quente, espontânea e cheia de atitude. A química física é uma das grandes forças desta combinação.",
        fortes=["Entusiasmo mútuo", "Iniciativa e coragem para enfrentar desafios"],
        atritos=["Disputa constante por liderança", "Impaciência e impulsividade"],
        conselho="Aprendam a ceder o protagonismo um ao outro para que a chama aqueça em vez de incendiar.",
        ideias=["Viajar para destinos aventureiros", "Praticar desportos ou atividades dinâmicas juntos"]
    ),
    ("Fogo", "Terra"): dict(
        tagline="A faísca e o solo firme",
        dinamica="{s1} e {s2} unem Fogo e Terra: de um lado, a vontade de expandir e arriscar; do outro, a necessidade de estabilidade e segurança.",
        amor="O romance cresce aos poucos e se fortalece com atitudes práticas e demonstrações leais de afeto.",
        comunicacao="Os ritmos de comunicação são diferentes: um é imediato e expansivo, o outro é ponderado e realista.",
        intimidade="A intimidade combina entrega e sensualidade. O Fogo traz o impulso, a Terra traz a consistência.",
        fortes=["Equilíbrio entre sonhar e realizar", "Lealdade que se solidifica com o tempo"],
        atritos=["Ritmos diferentes: pressa versus cautela", "Críticas à impulsividade do Fogo"],
        conselho="Decidam juntos quais riscos valem a pena e quais devem ser evitados para manter a paz.",
        ideias=["Piquenique em um lugar alto ao pôr do sol", "Cozinhar uma nova receita em casa"]
    ),
    ("Fogo", "Ar"): dict(
        tagline="O vento que atiça o fogo",
        dinamica="{s1} e {s2} formam uma das combinações mais estimulantes. O Ar alimenta o Fogo, criando ideias, conversas e projetos constantes.",
        amor="O amor é vivido como uma amizade apaixonada: vocês se divertem muito juntos e estimulam o crescimento intelectual um do outro.",
        comunicacao="A comunicação flui naturalmente, com troca de ideias rápida, bom humor e planos mirabolantes.",
        intimidade="A química é criativa e bem-humorada. A cumplicidade mental intensifica o desejo.",
        fortes=["Comunicação fácil e muito bom humor", "Liberdade e respeito pelo espaço individual"],
        atritos=["Superficialidade em momentos que pedem profundidade emocional", "Falta de foco prático"],
        conselho="Não deixem a leveza impedir conversas profundas quando surgirem conflitos.",
        ideias=["Viagem improvisada de fim de semana", "Noite de jogos ou debates divertidos"]
    ),
    ("Fogo", "Água"): dict(
        tagline="Vapor, mistério e transformação",
        dinamica="{s1} e {s2} unem Fogo e Água, dois elementos opostos. O Fogo quer ação exterior; a Água busca profundidade e recolhimento emocional.",
        amor="O romance é marcado por paixão e emoção à flor da pele, mas exige cuidado para não ferir sensibilidades.",
        comunicacao="O fogo se expressa de forma direta e a água sente as coisas de forma profunda, exigindo tato e empatia.",
        intimidade="A atração é forte e carregada de emoção. A intensidade pode ser magnética, mas requer vulnerabilidade.",
        fortes=["Paixão e magnetismo intensos", "Capacidade de se transformarem mutuamente"],
        atritos=["Sensibilidade ferida por palavras impulsivas", "Choque entre a pressa do Fogo e o tempo da Água"],
        conselho="Falem com cuidado e escutem com atenção. Quando houver conflito, o acolhimento vence a discussão.",
        ideias=["Jantar à luz de velas com música", "Banho de mar ou passeio à beira da água"]
    ),
    ("Terra", "Terra"): dict(
        tagline="Raízes fortes, futuro sólido",
        dinamica="{s1} e {s2} compartilham o elemento Terra: valorizam a segurança, a estabilidade e a construção a longo prazo.",
        amor="O amor se expressa em atitudes: cuidar, estar presente, organizar o futuro e criar um porto seguro um para o outro.",
        comunicacao="Vocês são objetivos e práticos. Falta, às vezes, um pouco de ousadia poética, mas entendem-se às mil maravilhas no dia a dia.",
        intimidade="A intimidade é sensorial, calorosa e cheia de toque, construída com base na confiança mútua e no relaxamento.",
        fortes=["Segurança e confiança mútua", "Planejamento e capacidade de concretizar sonhos"],
        atritos=["Rotina que pode virar monotonia", "Teimosia quando batem de frente"],
        conselho="Permitam-se sair da rotina e experimentar coisas novas para manter a chama acesa.",
        ideias=["Construir um projeto ou meta em conjunto", "Um fim de semana relaxante na natureza"]
    )
}

ELEMENTOS = {
    "Áries": "Fogo", "Leão": "Fogo", "Sagitário": "Fogo",
    "Touro": "Terra", "Virgem": "Terra", "Capricórnio": "Terra",
    "Gêmeos": "Ar", "Libra": "Ar", "Aquário": "Ar",
    "Câncer": "Água", "Escorpião": "Água", "Peixes": "Água"
}

def obter_elemento(signo):
    return ELEMENTOS.get(signo, "Fogo")

def gerar_pdf_mapa(nome1, signo1, nome2, signo2, email):
    elem1 = obter_elemento(signo1)
    elem2 = obter_elemento(signo2)
    
    chave = (elem1, elem2)
    if chave not in COMPATIBILIDADE:
        chave = (elem2, elem1)
    
    dados = COMPATIBILIDADE.get(chave, COMPATIBILIDADE[("Fogo", "Fogo")])
    
    filename = f"Mapa_Astral_Casal_{nome1}_e_{nome2}.pdf".replace(" ", "_")
    filepath = os.path.join(PDF_DIR, filename)
    
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=22, textColor=colors.HexColor('#6b21a8'), alignment=1, spaceAfter=15)
    subtitle_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=12, textColor=colors.HexColor('#4b5563'), alignment=1, spaceAfter=20)
    heading_style = ParagraphStyle('HeadStyle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor('#7c3aed'), spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#1f2937'), leading=14, spaceAfter=8)
    
    story = []
    
    story.append(Paragraph("✨ Mapa Astral do Casal ✨", title_style))
    story.append(Paragraph(f"<b>{nome1}</b> ({signo1}) & <b>{nome2}</b> ({signo2})", subtitle_style))
    story.append(Paragraph(f"<b>Tagline:</b> {dados['tagline']}", body_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("Dinâmica da Relação", heading_style))
    story.append(Paragraph(dados['dinamica'].format(s1=nome1, s2=nome2), body_style))
    
    story.append(Paragraph("Amores e Afetos", heading_style))
    story.append(Paragraph(dados['amor'], body_style))
    
    story.append(Paragraph("Comunicação", heading_style))
    story.append(Paragraph(dados['comunicacao'], body_style))
    
    story.append(Paragraph("Intimidade", heading_style))
    story.append(Paragraph(dados['intimidade'], body_style))
    
    story.append(Paragraph("Pontos Fortes", heading_style))
    for f in dados['fortes']:
        story.append(Paragraph(f"• {f}", body_style))
        
    story.append(Paragraph("Atritos e Desafios", heading_style))
    for a in dados['atritos']:
        story.append(Paragraph(f"• {a}", body_style))
        
    story.append(Paragraph("Conselho Estrelar", heading_style))
    story.append(Paragraph(dados['conselho'], body_style))
    
    doc.build(story)
    return filename

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mapa Astral do Casal</title>
        <style>
            body { font-family: sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; box-sizing: border-box; }
            .container { width: 100%; max-width: 500px; background: #1e293b; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
            h1 { color: #c084fc; text-align: center; font-size: 22px; }
            label { display: block; margin-top: 12px; font-weight: bold; color: #cbd5e1; font-size: 14px; }
            input, select { width: 100%; padding: 10px; margin-top: 5px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; box-sizing: border-box; font-size: 14px; }
            input::placeholder { color: #64748b; }
            .btn { display: block; width: 100%; background-color: #9333ea; color: white; padding: 12px; text-decoration: none; border: none; border-radius: 6px; font-weight: bold; margin-top: 20px; cursor: pointer; text-align: center; font-size: 16px; transition: background 0.2s; }
            .btn:hover { background-color: #7e22ce; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✨ Mapa Astral do Casal ✨</h1>
            <form action="/gerar" method="POST">
                <label>Nome do Parceiro 1:</label>
                <input type="text" name="nome1" required placeholder="Ex: Ana">
                
                <label>Signo do Parceiro 1:</label>
                <select name="signo1">
                    <option value="Áries">Áries</option>
                    <option value="Leão">Leão</option>
                    <option value="Sagitário">Sagitário</option>
                    <option value="Touro">Touro</option>
                    <option value="Virgem">Virgem</option>
                    <option value="Capricórnio">Capricórnio</option>
                    <option value="Gêmeos">Gêmeos</option>
                    <option value="Libra">Libra</option>
                    <option value="Aquário">Aquário</option>
                    <option value="Câncer">Câncer</option>
                    <option value="Escorpião">Escorpião</option>
                    <option value="Peixes">Peixes</option>
                </select>

                <label>Nome do Parceiro 2:</label>
                <input type="text" name="nome2" required placeholder="Ex: Bruno">
                
                <label>Signo do Parceiro 2:</label>
                <select name="signo2">
                    <option value="Áries">Áries</option>
                    <option value="Leão">Leão</option>
                    <option value="Sagitário">Sagitário</option>
                    <option value="Touro">Touro</option>
                    <option value="Virgem">Virgem</option>
                    <option value="Capricórnio">Capricórnio</option>
                    <option value="Gêmeos">Gêmeos</option>
                    <option value="Libra">Libra</option>
                    <option value="Aquário">Aquário</option>
                    <option value="Câncer">Câncer</option>
                    <option value="Escorpião">Escorpião</option>
                    <option value="Peixes">Peixes</option>
                </select>

                <label>E-mail para contacto:</label>
                <input type="email" name="email" required placeholder="exemplo@email.com">

                <button type="submit" class="btn">Gerar Mapa Astral</button>
            </form>
        </div>
    </body>
    </html>
    """

@app.route('/gerar', methods=['POST'])
def gerar():
    nome1 = request.form.get('nome1', 'Parceiro 1')
    signo1 = request.form.get('signo1', 'Áries')
    nome2 = request.form.get('nome2', 'Parceiro 2')
    signo2 = request.form.get('signo2', 'Áries')
    email = request.form.get('email', 'teste@email.com')
    
    filename = gerar_pdf_mapa(nome1, signo1, nome2, signo2, email)
    
    return f"""
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mapa Gerado</title>
        <style>
            body {{ font-family: sans-serif; background-color: #0f172a; color: #f8fafc; text-align: center; padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; box-sizing: border-box; }}
            .container {{ width: 100%; max-width: 500px; background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }}
            h1 {{ color: #c084fc; font-size: 22px; }}
            p {{ color: #cbd5e1; font-size: 14px; }}
            .btn {{ display: inline-block; background-color: #9333ea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; transition: background 0.2s; font-size: 16px; }}
            .btn:hover {{ background-color: #7e22ce; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✨ Mapa Gerado com Sucesso! ✨</h1>
            <p>Obrigado, {email}! O mapa astral de {nome1} e {nome2} foi criado com sucesso.</p>
            <br>
            <a href="/download/{filename}" class="btn">📥 Descarregar PDF do Mapa</a>
        </div>
    </body>
    </html>
    """

@app.route('/download/<path:filename>')
def download_file(filename):
    return send_file(os.path.join(PDF_DIR, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
