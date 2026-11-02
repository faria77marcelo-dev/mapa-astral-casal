import os
import re
import math
import random
from datetime import datetime
from xml.sax.saxutils import escape

from flask import Flask, request, send_file
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, NextPageTemplate, PageBreak,
    Paragraph, Spacer, Table, TableStyle, KeepTogether, Flowable,
)

app = Flask(__name__)

PDF_DIR = os.path.join(os.getcwd(), 'generated_pdfs')
os.makedirs(PDF_DIR, exist_ok=True)

# ==========================================
# 0. PALETA, FONTES E CONSTANTES
# ==========================================

W, H = 360, 780  # formato de tela de celular (antes: letter)
MARGEM = 20
LARGURA = W - 2 * MARGEM

ROXO_NOITE = colors.HexColor('#150726')
ROXO_PROFUNDO = colors.HexColor('#2E1065')
ROXO = colors.HexColor('#5B21B6')
ROXO_VIVO = colors.HexColor('#7C3AED')
LILAS = colors.HexColor('#A78BFA')
LILAS_CLARO = colors.HexColor('#DDD6FE')
LILAS_FUNDO = colors.HexColor('#F3EEFF')
FUNDO_PAGINA = colors.HexColor('#FBF9FF')
OURO = colors.HexColor('#D4AF37')
OURO_ESCURO = colors.HexColor('#A8821F')
CREME = colors.HexColor('#FFF8E6')
TEXTO = colors.HexColor('#3B3552')

HEX_OURO = '#D4AF37'
HEX_LILAS = '#A78BFA'
HEX_ROXO = '#5B21B6'

FONTE_SIMBOLOS = None

def registrar_fonte_simbolos():
    global FONTE_SIMBOLOS
    candidatos = [
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "C:\\Windows\\Fonts\\seguisym.ttf",
    ]
    try:
        import matplotlib
        candidatos.append(os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSans.ttf"))
    except Exception:
        pass
    for caminho in candidatos:
        try:
            if os.path.exists(caminho):
                pdfmetrics.registerFont(TTFont("Simbolos", caminho))
                FONTE_SIMBOLOS = "Simbolos"
                return
        except Exception:
            continue

registrar_fonte_simbolos()

def sym(ch, size=None, cor=None):
    if not FONTE_SIMBOLOS:
        return ""
    attrs = f'name="{FONTE_SIMBOLOS}"'
    if size:
        attrs += f' size="{size}"'
    if cor:
        attrs += f' color="{cor}"'
    return f'<font {attrs}>{ch}</font>'


# ==========================================
# 1. BANCO DE CONTEÚDO ASTROLÓGICO
# ==========================================

ZODIACO = [
    ("Áries", "♈"), ("Touro", "♉"), ("Gêmeos", "♊"), ("Câncer", "♋"),
    ("Leão", "♌"), ("Virgem", "♍"), ("Libra", "♎"), ("Escorpião", "♏"),
    ("Sagitário", "♐"), ("Capricórnio", "♑"), ("Aquário", "♒"), ("Peixes", "♓"),
]

# Mapeamento de signo para um mês/dia representativo para o sistema funcionar perfeitamente
DATAS_REF_SIGNOS = {
    "Áries": (4, 5), "Touro": (5, 5), "Gêmeos": (6, 5), "Câncer": (7, 5),
    "Leão": (8, 5), "Virgem": (9, 5), "Libra": (10, 5), "Escorpião": (11, 5),
    "Sagitário": (12, 5), "Capricórnio": (1, 5), "Aquário": (2, 5), "Peixes": (3, 5)
}

SIGNOS = {
    "Áries": dict(
        elem="Fogo", mod="Cardinal", planeta="Marte", psimb="♂",
        kw="Coragem · Iniciativa · Paixão",
        perfil="Ama com coragem e entusiasmo: conquista, toma a iniciativa e transforma o relacionamento em aventura.",
        ling="admiração, desafios a dois e demonstrações diretas de desejo.",
        precisa="um parceiro que acompanhe seu ritmo e respeite sua independência.",
        cuidado="a impaciência e o impulso de vencer discussões.",
        pedra="Cornalina", cor="Vermelho", dia="Terça-feira", nums="9 e 18"),
    "Touro": dict(
        elem="Terra", mod="Fixo", planeta="Vênus", psimb="♀",
        kw="Lealdade · Sensualidade · Constância",
        perfil="Ama com lealdade, sensualidade e constância; constrói o amor com gestos concretos e muita presença.",
        ling="carinho físico, tempo de qualidade e pequenos mimos.",
        precisa="segurança, rotina afetuosa e palavra cumprida.",
        cuidado="a teimosia e o apego excessivo ao conforto.",
        pedra="Quartzo rosa", cor="Verde e rosa", dia="Sexta-feira", nums="6 e 15"),
    "Gêmeos": dict(
        elem="Ar", mod="Mutável", planeta="Mercúrio", psimb="☿",
        kw="Curiosidade · Humor · Versatilidade",
        perfil="Ama com leveza, curiosidade e muita conversa; precisa de estímulo mental para manter a chama acesa.",
        ling="conversas longas, humor e novidades.",
        precisa="liberdade para explorar e um parceiro que seja também o melhor amigo.",
        cuidado="a dispersão e a dificuldade de falar de sentimentos profundos.",
        pedra="Citrino", cor="Amarelo", dia="Quarta-feira", nums="5 e 14"),
    "Câncer": dict(
        elem="Água", mod="Cardinal", planeta="Lua", psimb="☽",
        kw="Acolhimento · Memória afetiva · Proteção",
        perfil="Ama de forma protetora e profunda; cria um ninho emocional e guarda cada memória do casal.",
        ling="acolhimento, atenção aos detalhes e presença nos momentos difíceis.",
        precisa="segurança emocional e a certeza de ser prioridade.",
        cuidado="o retraimento quando se magoa e as oscilações de humor.",
        pedra="Pedra da lua", cor="Prata e branco", dia="Segunda-feira", nums="2 e 7"),
    "Leão": dict(
        elem="Fogo", mod="Fixo", planeta="Sol", psimb="☉",
        kw="Generosidade · Romance · Brilho",
        perfil="Ama com generosidade, calor e romantismo; quer viver uma história digna de cinema.",
        ling="elogios sinceros, surpresas e reconhecimento.",
        precisa="admiração, lealdade e alguém que celebre suas conquistas.",
        cuidado="o orgulho ferido e a necessidade de ser o centro das atenções.",
        pedra="Olho de tigre", cor="Dourado", dia="Domingo", nums="1 e 10"),
    "Virgem": dict(
        elem="Terra", mod="Mutável", planeta="Mercúrio", psimb="☿",
        kw="Cuidado · Dedicação · Discernimento",
        perfil="Ama servindo: cuida, organiza e demonstra carinho em atitudes práticas e atenciosas.",
        ling="ajuda no dia a dia, atenção aos detalhes e compromisso.",
        precisa="sinceridade, estabilidade e respeito aos seus cuidados.",
        cuidado="a autocrítica e a mania de apontar falhas.",
        pedra="Amazonita", cor="Verde e bege", dia="Quarta-feira", nums="5 e 23"),
    "Libra": dict(
        elem="Ar", mod="Cardinal", planeta="Vênus", psimb="♀",
        kw="Harmonia · Romantismo · Parceria",
        perfil="Ama a parceria: busca equilíbrio, beleza e harmonia, e é romântico por natureza.",
        ling="gentileza, momentos a dois e atenção estética, como flores, jantares e bons programas.",
        precisa="diálogo, reciprocidade e um ambiente sem conflitos.",
        cuidado="a indecisão e o hábito de evitar conversas difíceis.",
        pedra="Jade", cor="Rosa-claro e azul", dia="Sexta-feira", nums="6 e 24"),
    "Escorpião": dict(
        elem="Água", mod="Fixo", planeta="Plutão", psimb="♇",
        kw="Intensidade · Lealdade · Magnetismo",
        perfil="Ama com intensidade e entrega total; quando confia, mergulha fundo e não faz nada pela metade.",
        ling="lealdade, intimidade e conversas sinceras.",
        precisa="confiança absoluta e transparência.",
        cuidado="o ciúme e a tendência a guardar mágoas.",
        pedra="Obsidiana", cor="Vinho", dia="Terça-feira", nums="8 e 11"),
    "Sagitário": dict(
        elem="Fogo", mod="Mutável", planeta="Júpiter", psimb="♃",
        kw="Aventura · Otimismo · Liberdade",
        perfil="Ama com liberdade, otimismo e senso de aventura; quer um parceiro de viagem para a vida.",
        ling="experiências novas, sinceridade e bom humor.",
        precisa="espaço, confiança e um horizonte compartilhado.",
        cuidado="a franqueza excessiva e o medo de se prender.",
        pedra="Turquesa", cor="Roxo e azul", dia="Quinta-feira", nums="3 e 12"),
    "Capricórnio": dict(
        elem="Terra", mod="Cardinal", planeta="Saturno", psimb="♄",
        kw="Compromisso · Maturidade · Ambição",
        perfil="Ama com seriedade e compromisso; demonstra amor construindo um futuro sólido.",
        ling="apoio concreto, planos de longo prazo e respeito.",
        precisa="uma parceria madura e alguém que valorize seu esforço.",
        cuidado="a contenção emocional e o excesso de trabalho.",
        pedra="Granada", cor="Marrom e cinza", dia="Sábado", nums="4 e 8"),
    "Aquário": dict(
        elem="Ar", mod="Fixo", planeta="Urano", psimb="♅",
        kw="Originalidade · Amizade · Liberdade",
        perfil="Ama com originalidade e amizade; valoriza a mente, a liberdade e a autenticidade do outro.",
        ling="companheirismo intelectual, respeito à individualidade e ideias em comum.",
        precisa="liberdade, cumplicidade e espaço para ser diferente.",
        cuidado="o distanciamento emocional.",
        pedra="Ametista", cor="Azul-elétrico e violeta", dia="Sábado", nums="7 e 11"),
    "Peixes": dict(
        elem="Água", mod="Mutável", planeta="Netuno", psimb="♆",
        kw="Empatia · Sensibilidade · Intuição",
        perfil="Ama com sensibilidade, entrega e romantismo; vive o amor como uma experiência quase espiritual.",
        ling="gestos delicados, música, silêncio compartilhado e empatia.",
        precisa="ternura, paciência e proteção emocional.",
        cuidado="a tendência a idealizar e a fugir dos conflitos.",
        pedra="Água-marinha", cor="Verde-mar e lilás", dia="Quinta-feira", nums="7 e 12"),
}

PLANETAS = {
    "Marte": "Planeta da ação, do desejo e da coragem. Traz iniciativa, atração física e vontade de conquistar.",
    "Vênus": "Planeta do amor, do prazer e da harmonia. Traz afeto, sensualidade e senso de beleza.",
    "Mercúrio": "Planeta da mente e da comunicação. Traz curiosidade, humor e facilidade de dialogar.",
    "Lua": "Astro das emoções e do acolhimento. Traz sensibilidade, memória afetiva e cuidado.",
    "Sol": "Astro da vitalidade e do brilho pessoal. Traz generosidade, calor e vontade de viver grandes histórias.",
    "Plutão": "Planeta da transformação e da profundidade. Traz intensidade, entrega e poder de renovação.",
    "Júpiter": "Planeta da expansão e da fé. Traz otimismo, aventura e vontade de crescer junto.",
    "Saturno": "Planeta da estrutura e do compromisso. Traz maturidade, constância e visão de longo prazo.",
    "Urano": "Planeta da liberdade e da originalidade. Traz autenticidade, surpresa e mente inovadora.",
    "Netuno": "Planeta dos sonhos e da intuição. Traz romantismo, empatia e conexão sensível.",
}

ELEMENTOS = {
    "Fogo": "Energia, coragem e entusiasmo. Move a relação com paixão, iniciativa e vontade de viver intensamente.",
    "Terra": "Estabilidade, sensualidade e lealdade. Dá raízes, segurança e senso prático ao vínculo.",
    "Ar": "Mente, comunicação e liberdade. Traz leveza, ideias e companheirismo à relação.",
    "Água": "Emoção, intuição e profundidade. Cria acolhimento e uma conexão que vai além das palavras.",
}

ORDEM_ELEM = ["Fogo", "Terra", "Ar", "Água"]
ORDEM_MOD = ["Cardinal", "Fixo", "Mutável"]

CATEGORIAS = [
    "Amor & Romance", "Comunicação", "Química & Intimidade",
    "Confiança & Lealdade", "Futuro a Dois", "Diversão & Cumplicidade",
]

BASE_SCORES = {
    ("Fogo", "Fogo"): [85, 78, 93, 74, 68, 95],
    ("Fogo", "Terra"): [68, 62, 74, 72, 76, 64],
    ("Fogo", "Ar"): [88, 90, 86, 78, 74, 96],
    ("Fogo", "Água"): [74, 62, 90, 70, 64, 72],
    ("Terra", "Terra"): [86, 80, 82, 94, 95, 66],
    ("Terra", "Ar"): [64, 60, 66, 68, 66, 70],
    ("Terra", "Água"): [92, 86, 88, 90, 92, 76],
    ("Ar", "Ar"): [82, 95, 76, 72, 70, 92],
    ("Ar", "Água"): [70, 64, 72, 68, 66, 74],
    ("Água", "Água"): [94, 88, 95, 90, 86, 78],
}

TEXTOS_ELEM = {
    ("Fogo", "Fogo"): dict(
        tagline="Duas chamas, uma só fogueira",
        dinamica="{s1} e {s2} compartilham o elemento Fogo: a relação nasce com entusiasmo, atração imediata e uma vontade enorme de viver tudo intensamente. Há ambição, humor e coragem de sobra — o casal tem energia para realizar projetos e transformar qualquer rotina em aventura. O desafio é manter a chama acesa sem deixá-la virar incêndio.",
        amor="No amor, vocês se admiram e se desafiam. A conquista nunca termina: ambos gostam de surpreender e de ser surpreendidos, e o romance tende a ser caloroso, divertido e cheio de gestos grandiosos.",
        comunicacao="A conversa é direta e sem rodeios, o que evita mal-entendidos, mas também pode gerar discussões acaloradas. A dica é combinar um tempo para esfriar a cabeça antes de resolver conflitos.",
        intimidade="A química é uma das marcas do casal: espontânea, criativa e com iniciativa dos dois lados. Quando o desejo encontra cumplicidade, a intimidade vira um espaço de brincadeira e confiança.",
        fortes=["Entusiasmo e energia contagiantes", "Admiração mútua e apoio aos sonhos um do outro", "Capacidade de se reconciliar rápido e seguir em frente"],
        atritos=["Disputas de ego e vontade de ter a última palavra", "Impulsividade nas discussões", "Dificuldade de lidar com a rotina e com a calmaria"],
        conselho="Transformem a competição em parceria: celebrem as vitórias do outro como se fossem suas e reservem momentos de calma para fortalecer a conexão emocional.",
        ideias=["Aula de dança ou esporte a dois", "Trilha ou viagem de aventura", "Jantar surpresa com direito a karaokê"]),
    ("Fogo", "Terra"): dict(
        tagline="A faísca e o solo firme",
        dinamica="{s1} e {s2} unem Fogo e Terra: de um lado, a vontade de agir, sonhar e arriscar; do outro, a praticidade, a paciência e o desejo de construir algo duradouro. Quando se respeitam, o fogo aquece a terra e a terra dá forma ao que o fogo inicia. Quando não, um pode achar o outro impulsivo demais e o outro, lento demais.",
        amor="O romance cresce aos poucos e se fortalece com atitudes: o lado de fogo traz entusiasmo e iniciativa; o lado de terra traz presença, lealdade e segurança. É uma combinação que aprende a amar na prática.",
        comunicacao="Os ritmos de comunicação são diferentes: um fala o que sente na hora, o outro precisa de tempo para processar. Paciência e clareza fazem toda a diferença.",
        intimidade="A intimidade combina entrega e sensualidade. O fogo traz a chama; a terra, o toque, a calma e a atenção aos detalhes que fazem o outro se sentir desejado.",
        fortes=["Equilíbrio entre sonhar e realizar", "Lealdade que se fortalece com o tempo", "Complementaridade: um motiva, o outro estrutura"],
        atritos=["Ritmos diferentes: pressa versus cautela", "Críticas que soam como desânimo ou imprudência", "Visões diferentes sobre dinheiro, riscos e planos"],
        conselho="Decidam juntos quais riscos valem a pena e quais planos precisam de mais tempo. Reconhecer o valor do jeito do outro é o segredo da parceria.",
        ideias=["Piquenique em um lugar alto ao pôr do sol", "Cozinhar uma receita nova juntos", "Planejar uma meta conjunta com etapas e comemorações"]),
    ("Fogo", "Ar"): dict(
        tagline="O vento que atiça o fogo",
        dinamica="{s1} e {s2} formam uma das combinações mais estimulantes do zodíaco: o Ar alimenta o Fogo e o Fogo dá direção ao Ar. A relação é leve, animada e cheia de ideias, com muita conversa, risadas e vontade de explorar o mundo juntos. Raramente há tédio.",
        amor="O amor é vivido como uma amizade apaixonada: vocês se divertem, se provocam e se incentivam. O romance é dinâmico, com planos, viagens e novidades constantes.",
        comunicacao="A comunicação flui naturalmente, com troca de ideias, humor e afinidade intelectual. É um dos grandes trunfos do casal.",
        intimidade="A química é criativa e bem-humorada. A cumplicidade mental alimenta o desejo, e a vontade de experimentar mantém a chama sempre viva.",
        fortes=["Comunicação fácil e muito bom humor", "Liberdade e incentivo mútuo", "Energia para viver aventuras e novos projetos"],
        atritos=["Superficialidade em momentos que pedem profundidade emocional", "Falta de constância quando a empolgação passa", "Dificuldade de lidar com ciúme ou carência"],
        conselho="Não deixem a leveza impedir conversas profundas. Reservem tempo para falar de sentimentos com a mesma naturalidade com que falam de planos.",
        ideias=["Viagem improvisada de fim de semana", "Noite de shows, jogos ou stand-up", "Curso novo feito a dois"]),
    ("Fogo", "Água"): dict(
        tagline="Vapor, mistério e transformação",
        dinamica="{s1} e {s2} unem Fogo e Água, dois elementos opostos e profundamente atraídos um pelo outro. A relação é intensa, magnética e emocionalmente transformadora: o Fogo traz coragem e ação; a Água, sensibilidade e profundidade. Juntos, produzem vapor — uma energia poderosa quando bem conduzida.",
        amor="O romance é marcado por paixão e emoção à flor da pele. Há momentos de entrega total e outros de choque, mas o vínculo costuma ser forte e inesquecível.",
        comunicacao="O fogo se expressa de forma direta e a água sente antes de falar. Para se entenderem, é preciso ouvir também o que fica nas entrelinhas.",
        intimidade="A atração é forte e carregada de emoção. A intimidade tem profundidade, entrega e uma conexão que vai além do físico.",
        fortes=["Paixão e magnetismo intensos", "Capacidade de se transformar e crescer um com o outro", "Lealdade profunda quando existe confiança"],
        atritos=["Sensibilidade ferida por palavras impulsivas", "Ciúmes, orgulho e mágoas guardadas", "Ritmos emocionais diferentes: ação rápida versus emoção profunda"],
        conselho="Falem com cuidado e escutem com atenção. Quando o fogo aprende a aquecer sem queimar e a água a acolher sem apagar, a relação se torna profundamente transformadora.",
        ideias=["Jantar à luz de velas com música", "Banho de mar ou de cachoeira", "Noite de filmes seguida de conversa sincera"]),
    ("Terra", "Terra"): dict(
        tagline="Raízes fortes, futuro sólido",
        dinamica="{s1} e {s2} compartilham o elemento Terra: valorizam estabilidade, lealdade e construção. A relação é segura, sensual e orientada a resultados, com planos concretos e rotinas que fazem sentido para os dois. É um casal que cresce devagar e se fortalece a cada ano.",
        amor="O amor se expressa em atitudes: cuidar, estar presente, cumprir o que promete. O romance é tranquilo, confiável e cheio de pequenos gestos de carinho.",
        comunicacao="Vocês são objetivos e práticos. Falta, às vezes, expressar sentimentos em voz alta, mas a confiança constrói o entendimento.",
        intimidade="A intimidade é sensorial, calorosa e cheia de presença. O toque, o conforto e a atenção aos detalhes fazem a conexão crescer.",
        fortes=["Segurança e confiança mútua", "Planejamento e capacidade de construir projetos e patrimônio", "Sensualidade e prazer nas pequenas coisas"],
        atritos=["Rotina que pode virar monotonia", "Teimosia e resistência a mudanças", "Contenção emocional: sentir muito e falar pouco"],
        conselho="Inovem de vez em quando: uma viagem, um hobby novo, um jantar fora do padrão. E lembrem-se de dizer eu te amo em voz alta, além de demonstrar.",
        ideias=["Dia de spa ou massagem a dois", "Jantar caprichado em casa", "Passeio por sítio, jardim ou vinícola"]),
    ("Terra", "Ar"): dict(
        tagline="Ideias que procuram chão",
        dinamica="{s1} e {s2} unem Terra e Ar: um valoriza o concreto, o seguro e o previsível; o outro, as ideias, a variedade e a liberdade. É uma relação de aprendizado: a Terra ensina o Ar a se enraizar, e o Ar ensina a Terra a enxergar além da rotina.",
        amor="O romance pede ajustes de ritmo: um quer constância e rotina afetuosa, o outro, novidade e espaço. Quando encontram o meio-termo, o casal ganha estabilidade com leveza.",
        comunicacao="A Terra é prática e direta; o Ar é conceitual e fala bastante. Valorizar o estilo do outro evita a sensação de não estar sendo ouvido.",
        intimidade="A conexão física cresce com confiança. A Terra oferece presença e sensualidade; o Ar, curiosidade e criatividade.",
        fortes=["Complementaridade entre razão prática e visão criativa", "Respeito pelas diferenças quando existe maturidade", "Capacidade de aprender um com o outro"],
        atritos=["Frieza percebida: um acha o outro distante, o outro acha o parceiro apegado à rotina", "Ritmos opostos entre segurança e liberdade", "Dificuldade de demonstrar emoções"],
        conselho="Combinem o que é inegociável (segurança, respeito) e o que pode ser flexível (rotina, programas). A curiosidade genuína pelo mundo do outro aproxima.",
        ideias=["Exposição, livraria ou café cultural", "Viagem curta com roteiro flexível", "Projeto criativo a dois: horta, decoração ou DIY"]),
    ("Terra", "Água"): dict(
        tagline="Jardim fértil para o amor",
        dinamica="{s1} e {s2} formam uma combinação naturalmente nutritiva: a Água hidrata a Terra e a Terra dá forma e contorno à Água. A relação é afetuosa, segura e emocionalmente conectada, com forte desejo de criar vínculos duradouros, lar e família.",
        amor="O amor é cuidadoso e profundo. Há romantismo, lealdade e a sensação de que o outro é um porto seguro.",
        comunicacao="A Água sente e a Terra concretiza: vocês se entendem muitas vezes sem precisar de muitas palavras e valorizam o cuidado atento.",
        intimidade="A intimidade é terna, sensual e emocionalmente rica. O toque e a presença criam um espaço de segurança e entrega.",
        fortes=["Acolhimento e segurança emocional", "Lealdade e desejo de construir um lar", "Sensibilidade alinhada à praticidade"],
        atritos=["Dependência emocional ou apego excessivo", "Tendência a evitar conflitos até que se acumulem", "Rotina confortável demais, que pode apagar a novidade"],
        conselho="Cuidem do romance mesmo na rotina: encontros planejados, viagens e novidades mantêm o jardim florido.",
        ideias=["Cozinhar juntos e provar bons vinhos", "Fim de semana em casa de campo ou na praia", "Montar um álbum de memórias do casal"]),
    ("Ar", "Ar"): dict(
        tagline="Duas mentes, um mesmo céu",
        dinamica="{s1} e {s2} compartilham o elemento Ar: a conexão começa pela mente, pela conversa e pela curiosidade. A relação é leve, sociável e estimulante, com muitas trocas de ideias, amizade genuína e liberdade para ser quem se é.",
        amor="O amor é vivido como parceria entre amigos: há companheirismo, humor e respeito à individualidade. O romance cresce com conversas e novas experiências.",
        comunicacao="É uma das combinações com melhor diálogo do zodíaco: vocês se entendem rápido e adoram trocar ideias.",
        intimidade="A atração é mental antes de ser física. Depois que a conexão intelectual acontece, a intimidade se torna lúdica e criativa.",
        fortes=["Comunicação excelente e muito bom humor", "Respeito pela liberdade de cada um", "Curiosidade e abertura para o novo"],
        atritos=["Racionalizar demais os sentimentos", "Distanciamento emocional em momentos de crise", "Dificuldade de se comprometer com decisões práticas"],
        conselho="Deem nome ao que sentem e transformem ideias em planos concretos. A profundidade emocional é o ingrediente que faz a conexão durar.",
        ideias=["Podcast, debate de ideias ou clube do livro a dois", "Viagem cultural", "Noite de jogos de tabuleiro"]),
    ("Ar", "Água"): dict(
        tagline="Entre a razão e a emoção",
        dinamica="{s1} e {s2} unem Ar e Água: a mente e o coração em diálogo. O Ar traz leveza, ideias e perspectiva; a Água traz sensibilidade, profundidade e intuição. Quando há escuta, a relação é rica e inspiradora; quando não, um pode se sentir exagerado e o outro, frio.",
        amor="O romance é cheio de nuances: há momentos de leveza e outros de profunda emoção. Vocês aprendem a amar de formas diferentes e se complementam.",
        comunicacao="O Ar explica, a Água sente. A chave é traduzir emoções em palavras e acolher sem racionalizar demais.",
        intimidade="A conexão física cresce quando existe segurança emocional. A leveza do Ar ajuda a Água a relaxar, e a profundidade da Água dá sentido ao desejo.",
        fortes=["Equilíbrio entre razão e emoção", "Capacidade de ver o mesmo assunto por ângulos diferentes", "Troca de sensibilidade e criatividade"],
        atritos=["Sensação de não ser compreendido", "Distância emocional versus carência", "Reações opostas diante de conflitos: falar versus se recolher"],
        conselho="Pratiquem a empatia: um escuta sem pressa, o outro explica sem se defender. A diferença vira riqueza quando existe respeito.",
        ideias=["Cinema seguido de conversa profunda", "Passeio na praia ao entardecer", "Troca de cartas de amor escritas à mão"]),
    ("Água", "Água"): dict(
        tagline="Dois oceanos que se encontram",
        dinamica="{s1} e {s2} compartilham o elemento Água: a conexão é emocional, intuitiva e profunda. Vocês sentem o outro antes mesmo de ele falar, e a relação tende a ser acolhedora, protetora e cheia de cumplicidade silenciosa.",
        amor="O amor é entrega e sensibilidade. Há romantismo, memória afetiva e vontade de criar um mundo só de vocês.",
        comunicacao="Muito é dito sem palavras, mas é importante verbalizar necessidades para evitar suposições.",
        intimidade="A intimidade é intensa, terna e profundamente emocional. Existe confiança para se mostrar vulnerável.",
        fortes=["Empatia e intuição afiadas", "Acolhimento mútuo", "Profundidade emocional e lealdade"],
        atritos=["Mágoas guardadas e silêncios", "Oscilações de humor que se amplificam", "Dificuldade de impor limites e de resolver conflitos com objetividade"],
        conselho="Criem o hábito de conversar sobre o que sentem antes que vire peso. Alguma estrutura e planos práticos dão firmeza ao oceano emocional.",
        ideias=["Noite de lareira, música e silêncio compartilhado", "Viagem à beira-mar", "Ritual de gratidão: cada um diz o que mais ama no outro"]),
}

TEXTOS_MOD = {
    ("Cardinal", "Cardinal"): "Dois iniciadores: a relação tem muitas ideias, projetos e iniciativas, mas é importante combinar quem lidera cada área para evitar disputas de comando.",
    ("Cardinal", "Fixo"): "Um inicia, o outro sustenta: a relação ganha direção e constância, desde que o signo fixo aceite mudanças e o cardinal respeite o tempo de maturação.",
    ("Cardinal", "Mutável"): "Um dá o rumo, o outro se adapta: uma combinação fluida e flexível, desde que o signo mutável também tenha voz nas decisões.",
    ("Fixo", "Fixo"): "Dois pilares: lealdade e persistência de sobra, mas atenção à teimosia. Aprender a ceder é o segredo da harmonia.",
    ("Fixo", "Mutável"): "Um traz estabilidade, o outro, adaptabilidade: ótimo equilíbrio, desde que o fixo não engesse e o mutável não se disperse.",
    ("Mutável", "Mutável"): "Dois camaleões: adaptáveis, curiosos e abertos ao novo, mas precisam criar rotinas e tomar decisões firmes para dar estrutura à relação.",
}

JORNADA = {
    ("Fogo", "Fogo"): [
        "Faísca imediata: atração intensa, desafios divertidos e a sensação de que o tempo voa quando estão juntos.",
        "Aparecem as disputas de ego. É a fase de aprender a competir menos e a torcer mais um pelo outro.",
        "Quando a admiração vence o orgulho, tornam-se uma dupla imbatível, sempre em busca da próxima aventura."],
    ("Fogo", "Terra"): [
        "O fogo encanta pela energia e a terra, pela firmeza. A curiosidade pelas diferenças move a aproximação.",
        "Ritmos distintos pedem acordos: quanto arriscar, quanto planejar e como dividir as decisões.",
        "Com respeito, constroem uma base sólida que sustenta grandes sonhos e conquistas compartilhadas."],
    ("Fogo", "Ar"): [
        "Conexão rápida, conversas sem fim e muita diversão. A relação parece leve e cheia de possibilidades.",
        "O desafio é dar profundidade e constância ao que começou como empolgação.",
        "Ao unir leveza e compromisso, viram parceiros de vida, de projetos e de viagens."],
    ("Fogo", "Água"): [
        "Atração magnética e intensa: tudo parece mais emocionante e misterioso.",
        "As diferenças de reação aparecem. É a fase de ouvir sem se defender e de falar sem ferir.",
        "Se cultivam confiança, a relação se aprofunda e se torna uma das mais marcantes do zodíaco."],
    ("Terra", "Terra"): [
        "Aproximação tranquila e segura: a confiança vai sendo construída a cada gesto e promessa cumprida.",
        "Planos concretos ganham forma: casa, finanças, projetos. O cuidado é não deixar o romance virar rotina.",
        "Um relacionamento sólido, duradouro e confortável, capaz de atravessar qualquer fase da vida."],
    ("Terra", "Ar"): [
        "A curiosidade mútua aproxima: um é atraído pela estabilidade, o outro pela mente inquieta.",
        "Ajustar liberdade e segurança vira o grande tema. Acordos claros evitam ruídos.",
        "Com maturidade, a Terra dá raízes às ideias do Ar e o Ar traz novos ares à Terra."],
    ("Terra", "Água"): [
        "Sintonia imediata: a sensação de acolhimento e de lar surge logo nos primeiros encontros.",
        "O vínculo se aprofunda com cuidado e rotina afetuosa. Atenção para manter a novidade viva.",
        "Uma parceria afetuosa e estável, com forte vocação para família, lar e projetos de longo prazo."],
    ("Ar", "Ar"): [
        "Começa pela conversa e pela amizade: horas de papo, risadas e ideias trocadas.",
        "O desafio é traduzir a sintonia mental em intimidade emocional e compromissos concretos.",
        "Com abertura emocional, tornam-se melhores amigos e cúmplices por toda a vida."],
    ("Ar", "Água"): [
        "Interesse curioso e delicado: um se encanta pela profundidade, o outro pela leveza.",
        "Fase de aprender a linguagem emocional do outro, equilibrando razão e sentimento.",
        "Quando há escuta verdadeira, a relação une inteligência e sensibilidade de forma rara."],
    ("Água", "Água"): [
        "Conexão profunda e quase intuitiva: a sensação de se conhecerem há muito tempo.",
        "É importante dar voz aos sentimentos e criar limites saudáveis para que as emoções não se acumulem.",
        "Uma ligação íntima, protetora e cheia de cumplicidade, capaz de atravessar qualquer tempestade."],
}

RITUAL = [
    ("Gratidão", "cada um escreve três coisas que admira no outro e lê em voz alta."),
    ("Presença", "uma hora sem celular e sem telas, só vocês dois."),
    ("Memória", "revejam fotos antigas e relembrem o primeiro encontro."),
    ("Aventura", "façam um dos programas ideais sugeridos neste mapa."),
    ("Conversa sincera", "compartilhem um sonho e um medo, sem interrupções nem julgamentos."),
    ("Gesto de amor", "surpreendam o outro usando a linguagem do amor dele."),
    ("Brinde", "celebrem a jornada e escolham juntos uma meta para o próximo mês."),
]

ESPECIAIS = {
    tuple(sorted(["Áries", "Escorpião"])): dict(
        dinamica="Fogo e Água — uma combinação de extrema intensidade, magnetismo e profunda transformação emocional. {s1} traz a coragem e a iniciativa; {s2}, a profundidade e a entrega. Juntos, vivem uma conexão que raramente passa despercebida.",
        fortes_0="Paixão avassaladora, proteção mútua e lealdade inabalável perante os desafios",
        atritos_0="O choque entre a impulsividade e o orgulho de Áries e a possessividade e a profundidade de Escorpião",
        conselho="Aprendam a ceder no timing certo, transformando as diferenças de temperamento num motor de crescimento a dois.",
    ),
}

def chave_elem(e1, e2):
    return tuple(sorted([e1, e2], key=ORDEM_ELEM.index))

def chave_mod(m1, m2):
    return tuple(sorted([m1, m2], key=ORDEM_MOD.index))

def calcular_scores(s1, s2):
    e1, e2 = SIGNOS[s1]["elem"], SIGNOS[s2]["elem"]
    base = BASE_SCORES[chave_elem(e1, e2)]
    semente = zlib.crc32("|".join(sorted([s1, s2])).encode("utf-8")) if 'zlib' in globals() else 123
    scores = []
    for i, b in enumerate(base):
        ajuste = ((semente >> (i * 3)) & 7) - 3
        scores.append(max(55, min(98, b + ajuste)))
    geral = round(sum(scores) / len(scores))
    return geral, scores

def obter_analise_exclusiva(signo1, signo2):
    d1, d2 = SIGNOS[signo1], SIGNOS[signo2]
    base = dict(TEXTOS_ELEM[chave_elem(d1["elem"], d2["elem"])])
    base["fortes"] = list(base["fortes"])
    base["atritos"] = list(base["atritos"])

    especial = ESPECIAIS.get(tuple(sorted([signo1, signo2])))
    if especial:
        if "dinamica" in especial:
            base["dinamica"] = especial["dinamica"]
        if "fortes_0" in especial:
            base["fortes"][0] = especial["fortes_0"]
        if "atritos_0" in especial:
            base["atritos"][0] = especial["atritos_0"]
        if "conselho" in especial:
            base["conselho"] = especial["conselho"]

    base["dinamica"] = base["dinamica"].format(s1=signo1, s2=signo2)
    base["ritmo"] = TEXTOS_MOD[chave_mod(d1["mod"], d2["mod"])]
    base["jornada"] = JORNADA[chave_elem(d1["elem"], d2["elem"])]
    return base


# ==========================================
# 2. COMPONENTES VISUAIS E DECORAÇÃO (formato celular)
# ==========================================

# Na roleta da capa, use True para desenhar os símbolos ♈ ♉ ... (precisa da fonte DejaVu).
# Com False, a roleta mostra as abreviações ÁRI, TOU, GÊM...
ROLETA_COM_SIMBOLOS = False

# As páginas de conteúdo são mais altas que a capa, para ter menos cortes entre as seções.
HC = 1000
ABREV_SIGNOS = ["ÁRI", "TOU", "GÊM", "CÂN", "LEÃ", "VIR", "LIB", "ESC", "SAG", "CAP", "AQU", "PEI"]

VERDE = colors.HexColor('#1F6B4A')
VERDE_CLARO = colors.HexColor('#2F9C6E')
LARANJA = colors.HexColor('#9A4A12')
LARANJA_CLARO = colors.HexColor('#E08A3C')
CINZA_SUAVE = colors.HexColor('#6B6384')
OURO_BORDA = colors.HexColor('#ECD68A')


def cap1(txt):
    return txt[:1].upper() + txt[1:] if txt else txt


class CaixaArredondada(Flowable):
    """Cartão com cantos arredondados que empilha outros elementos dentro."""

    def __init__(self, conteudo, largura, fundo=colors.white, borda=LILAS_CLARO,
                 espessura=0.9, raio=12, pad_x=16, pad_y=16):
        super().__init__()
        self.conteudo = conteudo
        self.largura = largura
        self.fundo = fundo
        self.borda = borda
        self.espessura = espessura
        self.raio = raio
        self.pad_x = pad_x
        self.pad_y = pad_y
        self._itens = []

    def wrap(self, aw, ah):
        interno = self.largura - 2 * self.pad_x
        self._itens = []
        total = 0
        for f in self.conteudo:
            _, h = f.wrap(interno, 10000)
            self._itens.append((f, h))
            total += h
        self.width = self.largura
        self.height = total + 2 * self.pad_y
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(self.fundo)
        c.setStrokeColor(self.borda)
        c.setLineWidth(self.espessura)
        c.roundRect(0, 0, self.width, self.height, self.raio, stroke=1, fill=1)
        y = self.height - self.pad_y
        for f, h in self._itens:
            y -= h
            f.drawOn(c, self.pad_x, y)


class Pilulas(Flowable):
    """Etiquetas (chips) que quebram de linha sozinhas."""

    def __init__(self, textos, largura, fonte="Helvetica-Bold", tam=12.5):
        super().__init__()
        self.textos = textos
        self.largura = largura
        self.fonte = fonte
        self.tam = tam
        self.alt = 25
        self.gap = 7

    def wrap(self, aw, ah):
        x, linha = 0, 0
        self.pos = []
        for t in self.textos:
            w = stringWidth(t, self.fonte, self.tam) + 24
            if x + w > self.largura and x > 0:
                x, linha = 0, linha + 1
            self.pos.append((x, linha, w, t))
            x += w + self.gap
        self.width = self.largura
        self.height = (linha + 1) * self.alt + linha * self.gap
        return self.width, self.height

    def draw(self):
        c = self.canv
        for x, l, w, t in self.pos:
            y = self.height - (l + 1) * self.alt - l * self.gap
            c.setFillColor(LILAS_FUNDO)
            c.setStrokeColor(LILAS_CLARO)
            c.setLineWidth(0.9)
            c.roundRect(x, y, w, self.alt, self.alt / 2, stroke=1, fill=1)
            c.setFillColor(ROXO_PROFUNDO)
            c.setFont(self.fonte, self.tam)
            c.drawCentredString(x + w / 2, y + self.alt / 2 - self.tam * 0.35, t)


class BarraCompat(Flowable):
    def __init__(self, rotulo, valor, largura, destaque=False):
        super().__init__()
        self.rotulo = rotulo
        self.valor = valor
        self.destaque = destaque
        self.width = largura
        self.height = 40

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        w = self.width
        c.setFillColor(TEXTO)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(0, 26, self.rotulo)
        c.setFillColor(ROXO_PROFUNDO)
        c.drawRightString(w, 26, f"{self.valor}%")
        c.setFillColor(LILAS_FUNDO)
        c.roundRect(0, 6, w, 11, 5.5, stroke=0, fill=1)
        c.setFillColor(OURO if self.destaque else ROXO_VIVO)
        c.roundRect(0, 6, max(12, w * self.valor / 100), 11, 5.5, stroke=0, fill=1)


class IconeElemento(Flowable):
    CORES = {
        "Fogo": colors.HexColor('#F97316'),
        "Terra": colors.HexColor('#65A30D'),
        "Ar": colors.HexColor('#0EA5E9'),
        "Água": colors.HexColor('#6366F1'),
    }

    def __init__(self, elem, size=46):
        super().__init__()
        self.elem = elem
        self.size = size
        self.width = size
        self.height = size

    def draw(self):
        c = self.canv
        s = self.size
        c.setFillColor(self.CORES[self.elem])
        c.circle(s / 2, s / 2, s / 2, stroke=0, fill=1)
        c.setStrokeColor(colors.white)
        c.setLineWidth(2)
        cx, cy, a = s / 2, s / 2, s * 0.26
        acima = self.elem in ("Fogo", "Ar")
        if acima:
            pts = [(cx, cy + a), (cx - a * 1.05, cy - a * 0.75), (cx + a * 1.05, cy - a * 0.75)]
            y_barra = cy - 0.05 * a
        else:
            pts = [(cx, cy - a), (cx - a * 1.05, cy + a * 0.75), (cx + a * 1.05, cy + a * 0.75)]
            y_barra = cy + 0.05 * a
        p = c.beginPath()
        p.moveTo(*pts[0])
        p.lineTo(*pts[1])
        p.lineTo(*pts[2])
        p.close()
        c.drawPath(p, stroke=1, fill=0)
        if self.elem in ("Ar", "Terra"):
            c.line(cx - a * 0.63, y_barra, cx + a * 0.63, y_barra)


class Jornada(Flowable):
    """Linha do tempo vertical com bolinhas numeradas."""

    def __init__(self, etapas, largura, est):
        super().__init__()
        self.etapas = etapas
        self.largura = largura
        self.est = est
        self.gap = 20
        self.bola = 28

    def wrap(self, aw, ah):
        tw = self.largura - 44
        self.blocos = []
        total = 0
        for n, titulo, texto in self.etapas:
            p1 = Paragraph(titulo.upper(), self.est['EtapaTitulo'])
            p2 = Paragraph(escape(texto), self.est['Corpo'])
            _, h1 = p1.wrap(tw, 10000)
            _, h2 = p2.wrap(tw, 10000)
            h = self.bola + 4 + h2
            self.blocos.append((n, p1, p2, h1, h2, h))
            total += h
        total += self.gap * (len(self.blocos) - 1)
        self.width = self.largura
        self.height = total
        return self.width, self.height

    def draw(self):
        c = self.canv
        y = self.height
        tops = []
        for b in self.blocos:
            tops.append(y)
            y -= b[5] + self.gap
        c.setStrokeColor(LILAS_CLARO)
        c.setLineWidth(2)
        for i in range(len(tops) - 1):
            c.line(self.bola / 2, tops[i] - self.bola, self.bola / 2, tops[i + 1])
        for top, (n, p1, p2, h1, h2, h) in zip(tops, self.blocos):
            c.setFillColor(OURO)
            c.circle(self.bola / 2, top - self.bola / 2, self.bola / 2, stroke=0, fill=1)
            c.setFillColor(ROXO_NOITE)
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(self.bola / 2, top - self.bola / 2 - 5, str(n))
            p1.drawOn(c, 44, top - self.bola / 2 - h1 / 2)
            p2.drawOn(c, 44, top - self.bola - 4 - h2)


class CartaoDia(Flowable):
    """Um dia do ritual: círculo com o número e texto ao lado."""

    def __init__(self, n, titulo, texto, largura, est):
        super().__init__()
        self.n = n
        self.titulo = titulo
        self.texto = texto
        self.largura = largura
        self.est = est
        self.circ = 50

    def wrap(self, aw, ah):
        tx = 16 + self.circ + 14
        tw = self.largura - tx - 14
        self.p1 = Paragraph(escape(self.titulo), self.est['DiaTitulo'])
        self.p2 = Paragraph(escape(self.texto), self.est['Corpo'])
        _, self.h1 = self.p1.wrap(tw, 10000)
        _, self.h2 = self.p2.wrap(tw, 10000)
        self.tx = tx
        self.width = self.largura
        self.height = max(self.circ, self.h1 + 3 + self.h2) + 28
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(colors.white)
        c.setStrokeColor(LILAS_CLARO)
        c.setLineWidth(0.9)
        c.roundRect(0, 0, self.width, self.height, 12, stroke=1, fill=1)
        topo = self.height - 14
        cx, cy = 16 + self.circ / 2, topo - self.circ / 2
        c.setFillColor(CREME)
        c.setStrokeColor(OURO)
        c.setLineWidth(1.8)
        c.circle(cx, cy, self.circ / 2, stroke=1, fill=1)
        c.setFillColor(CINZA_SUAVE)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(cx, cy + 9, "DIA")
        c.setFillColor(ROXO_PROFUNDO)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(cx, cy - 12, str(self.n))
        self.p1.drawOn(c, self.tx, topo - self.h1)
        self.p2.drawOn(c, self.tx, topo - self.h1 - 3 - self.h2)


def texto_esp(canvas, x, y, txt, fonte, tamanho, cor, espaco=0, alinhar='left'):
    total = stringWidth(txt, fonte, tamanho) + espaco * max(len(txt) - 1, 0)
    if alinhar == 'center':
        x = x - total / 2
    elif alinhar == 'right':
        x = x - total
    t = canvas.beginText(x, y)
    t.setFont(fonte, tamanho)
    t.setFillColor(cor)
    t.setCharSpace(espaco)
    t.textOut(txt)
    t.setCharSpace(0)
    canvas.drawText(t)


def texto_misto(canvas, cx, y, partes):
    total = sum(stringWidth(t, f, s) for t, f, s, _ in partes)
    x = cx - total / 2
    for txt, fonte, tam, cor in partes:
        canvas.setFont(fonte, tam)
        canvas.setFillColor(cor)
        canvas.drawString(x, y, txt)
        x += stringWidth(txt, fonte, tam)


def ornamento(canvas, cx, cy, meia=95):
    canvas.setStrokeColor(OURO)
    canvas.setLineWidth(0.8)
    canvas.line(cx - meia, cy, cx - 12, cy)
    canvas.line(cx + 12, cy, cx + meia, cy)
    canvas.setFillColor(OURO)
    p = canvas.beginPath()
    p.moveTo(cx, cy + 5)
    p.lineTo(cx + 5, cy)
    p.lineTo(cx, cy - 5)
    p.lineTo(cx - 5, cy)
    p.close()
    canvas.drawPath(p, stroke=0, fill=1)


def ajustar_fonte(txt, fonte, tamanho, largura_max):
    while tamanho > 12 and stringWidth(txt, fonte, tamanho) > largura_max:
        tamanho -= 1
    return tamanho


def desenhar_capa(canvas, doc, ctx):
    canvas.saveState()
    passos = 140
    topo = (0x15 / 255, 0x07 / 255, 0x26 / 255)
    base = (0x45 / 255, 0x1A / 255, 0x8C / 255)
    for i in range(passos):
        t = i / (passos - 1)
        canvas.setFillColorRGB(*[topo[k] + (base[k] - topo[k]) * t for k in range(3)])
        canvas.rect(0, H - (i + 1) * H / passos, W, H / passos + 1, stroke=0, fill=1)

    cx, cy = W / 2, 430
    for raio, alfa in [(270, 0.035), (230, 0.04), (195, 0.05)]:
        canvas.setFillColor(ROXO_VIVO)
        canvas.setFillAlpha(alfa)
        canvas.circle(cx, cy, raio, stroke=0, fill=1)
    canvas.setFillAlpha(1)

    rnd = random.Random(11)
    for _ in range(120):
        x, y = rnd.uniform(6, W - 6), rnd.uniform(6, H - 6)
        r = rnd.choice([0.5, 0.7, 0.9, 1.2, 1.5])
        canvas.setFillColor(rnd.choice([OURO, colors.white, LILAS]))
        canvas.setFillAlpha(rnd.choice([0.25, 0.4, 0.6, 0.8]))
        canvas.circle(x, y, r, stroke=0, fill=1)
    canvas.setFillAlpha(1)

    # Título
    ornamento(canvas, cx, H - 58, 85)
    texto_esp(canvas, cx, H - 96, "MAPA ASTRAL", "Helvetica-Bold", 30, colors.white, 6, 'center')
    texto_esp(canvas, cx, H - 124, "DO CASAL", "Helvetica", 14, OURO, 10, 'center')
    texto_esp(canvas, cx, H - 148, "UM OLHAR SOBRE A ENERGIA QUE UNE", "Helvetica", 9, LILAS, 2.4, 'center')
    texto_esp(canvas, cx, H - 162, "VOCÊ E SEU AMOR", "Helvetica", 9, LILAS, 2.4, 'center')

    # Roleta do zodíaco
    r_out = 160
    s = r_out / 192.0
    r_mid, r_a, r_b, r_lab, r_bola = 138 * s, 112 * s, 90 * s, 165 * s, 22 * s

    canvas.setFillColor(ROXO_NOITE)
    canvas.setFillAlpha(0.55)
    canvas.circle(cx, cy, r_out, stroke=0, fill=1)
    canvas.setFillColor(ROXO_PROFUNDO)
    canvas.circle(cx, cy, r_mid, stroke=0, fill=1)
    canvas.setFillAlpha(1)
    canvas.setStrokeColor(OURO)
    canvas.setLineWidth(1.6)
    canvas.circle(cx, cy, r_out, stroke=1, fill=0)
    canvas.setLineWidth(1.2)
    canvas.circle(cx, cy, r_mid, stroke=1, fill=0)
    canvas.setStrokeColor(OURO)
    canvas.setLineWidth(0.6)
    canvas.setStrokeAlpha(0.35)
    canvas.circle(cx, cy, r_a, stroke=1, fill=0)
    canvas.setStrokeAlpha(0.25)
    canvas.circle(cx, cy, r_b, stroke=1, fill=0)

    canvas.setStrokeColor(OURO)
    canvas.setLineWidth(0.8)
    canvas.setStrokeAlpha(0.7)
    for i in range(12):
        ang = math.radians(90 - i * 30 + 15)
        canvas.line(cx + r_mid * math.cos(ang), cy + r_mid * math.sin(ang),
                    cx + r_out * math.cos(ang), cy + r_out * math.sin(ang))
    canvas.setStrokeAlpha(1)

    nomes_signos = [n for n, _ in ZODIACO]
    idx_casal = [nomes_signos.index(ctx["s1"]), nomes_signos.index(ctx["s2"])]

    def pos_signo(i):
        ang = math.radians(90 - i * 30)
        return cx + r_lab * math.cos(ang), cy + r_lab * math.sin(ang)

    if idx_casal[0] != idx_casal[1]:
        (xa, ya), (xb, yb) = pos_signo(idx_casal[0]), pos_signo(idx_casal[1])
        canvas.setStrokeColor(OURO)
        canvas.setLineWidth(1.6)
        canvas.line(xa, ya, xb, yb)

    for i, (nome, simb) in enumerate(ZODIACO):
        x, y = pos_signo(i)
        destaque = i in idx_casal
        if destaque:
            canvas.setFillColor(OURO)
            canvas.circle(x, y, r_bola, stroke=0, fill=1)
        canvas.setFillColor(ROXO_NOITE if destaque else colors.white)
        if ROLETA_COM_SIMBOLOS and FONTE_SIMBOLOS:
            canvas.setFont(FONTE_SIMBOLOS, 20)
            canvas.drawCentredString(x, y - 7, simb)
        else:
            canvas.setFont("Helvetica-Bold", 10.5)
            canvas.drawCentredString(x, y - 3.7, ABREV_SIGNOS[i])

    for nome, dy in [(ctx["nome1"], 17), (ctx["nome2"], -42)]:
        tam = ajustar_fonte(nome, "Times-Bold", 30, 175)
        canvas.setFont("Times-Bold", tam)
        canvas.setFillColor(colors.white)
        canvas.drawCentredString(cx, cy + dy, nome)
    canvas.setFillColor(OURO)
    canvas.setFont("Times-Bold", 26)
    canvas.drawCentredString(cx, cy - 11, "&")

    # Pontuação e frase
    canvas.setFont("Times-Bold", 58)
    canvas.setFillColor(OURO)
    canvas.drawCentredString(cx, 204, f"{ctx['geral']}%")
    texto_esp(canvas, cx, 180, "AFINIDADE ASTRAL", "Helvetica", 9, LILAS_CLARO, 4, 'center')
    ornamento(canvas, cx, 162, 55)

    tam_tag = ajustar_fonte(ctx["tagline"], "Times-Italic", 21, LARGURA)
    canvas.setFont("Times-Italic", tam_tag)
    canvas.setFillColor(colors.white)
    canvas.drawCentredString(cx, 130, ctx["tagline"])

    texto_misto(canvas, cx, 98, [
        (ctx["s1"].upper(), "Helvetica-Bold", 11, LILAS_CLARO),
        ("    •    ", "Helvetica", 11, OURO),
        (ctx["s2"].upper(), "Helvetica-Bold", 11, LILAS_CLARO),
    ])
    texto_esp(canvas, cx, 54, f"GERADO EM {datetime.now().strftime('%d/%m/%Y')}", "Helvetica", 7.5, LILAS, 2.2, 'center')
    canvas.restoreState()


def desenhar_pagina(canvas, doc, ctx):
    canvas.saveState()
    canvas.setFillColor(FUNDO_PAGINA)
    canvas.rect(0, 0, W, HC, stroke=0, fill=1)

    canvas.setFillColor(ROXO_PROFUNDO)
    canvas.rect(0, HC - 28, W, 28, stroke=0, fill=1)
    canvas.setFillColor(OURO)
    canvas.rect(0, HC - 30, W, 2, stroke=0, fill=1)
    texto_esp(canvas, MARGEM, HC - 18, "MAPA ASTRAL DO CASAL", "Helvetica-Bold", 7, OURO, 2.6)
    canvas.setFont("Times-Italic", 11)
    canvas.setFillColor(LILAS_CLARO)
    canvas.drawRightString(W - MARGEM, HC - 19, f"{ctx['nome1']} & {ctx['nome2']}")

    canvas.setStrokeColor(LILAS_CLARO)
    canvas.setLineWidth(0.8)
    canvas.line(MARGEM, 34, W - MARGEM, 34)
    canvas.setFillColor(OURO_ESCURO)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawCentredString(W / 2, 17, str(canvas.getPageNumber()))
    texto_esp(canvas, MARGEM, 18, f"{ctx['s1'].upper()} & {ctx['s2'].upper()}", "Helvetica", 6.5, CINZA_SUAVE, 1.6)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(CINZA_SUAVE)
    canvas.drawRightString(W - MARGEM, 18, datetime.now().strftime("%d/%m/%Y"))
    canvas.restoreState()


# ==========================================
# 3. ESTILOS E FUNÇÕES DE GERAÇÃO DO PDF
# ==========================================

def criar_estilos():
    base = getSampleStyleSheet()['Normal']

    def S(nome, **kw):
        return ParagraphStyle(nome, parent=base, **kw)

    def item(nome, cor):
        return S(nome, fontName='Helvetica', fontSize=14, leading=21, textColor=TEXTO,
                 leftIndent=17, bulletIndent=0, bulletFontName='Helvetica-Bold',
                 bulletFontSize=17, bulletColor=cor, spaceAfter=8)

    return {
        'Corpo': S('Corpo', fontName='Helvetica', fontSize=14, leading=21.5, textColor=TEXTO),
        'CorpoEscuro': S('CorpoEscuro', fontName='Helvetica', fontSize=14, leading=21.5, textColor=colors.white),
        'CorpoCentro': S('CorpoCentro', fontName='Helvetica', fontSize=13.5, leading=20.5, textColor=LILAS_CLARO, alignment=TA_CENTER),
        'Sutil': S('Sutil', fontName='Helvetica', fontSize=12.5, leading=18, textColor=CINZA_SUAVE),
        'Eyebrow': S('Eyebrow', fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=ROXO, spaceAfter=5),
        'EyebrowOuro': S('EyebrowOuro', fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=OURO, spaceAfter=5),
        'EyebrowCentro': S('EyebrowCentro', fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=OURO, alignment=TA_CENTER, spaceAfter=8),
        'TituloSecao': S('TituloSecao', fontName='Times-Bold', fontSize=21, leading=24, textColor=ROXO_PROFUNDO),
        'NomeCard': S('NomeCard', fontName='Times-Bold', fontSize=23, leading=26, textColor=ROXO_PROFUNDO),
        'Titulo3': S('Titulo3', fontName='Helvetica-Bold', fontSize=14.5, leading=19, textColor=ROXO_PROFUNDO),
        'TituloVerde': S('TituloVerde', fontName='Helvetica-Bold', fontSize=14.5, leading=19, textColor=VERDE, spaceAfter=10),
        'TituloLaranja': S('TituloLaranja', fontName='Helvetica-Bold', fontSize=14.5, leading=19, textColor=LARANJA, spaceAfter=10),
        'Termo': S('Termo', fontName='Helvetica-Bold', fontSize=9.5, leading=12, textColor=ROXO, spaceAfter=1),
        'EtapaTitulo': S('EtapaTitulo', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=ROXO),
        'DiaTitulo': S('DiaTitulo', fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=ROXO_PROFUNDO),
        'NotaRotulo': S('NotaRotulo', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=CINZA_SUAVE, spaceAfter=2),
        'NotaTexto': S('NotaTexto', fontName='Helvetica', fontSize=13, leading=18, textColor=TEXTO),
        'Mensagem': S('Mensagem', fontName='Times-Italic', fontSize=21, leading=29, textColor=colors.white, alignment=TA_CENTER),
        'Aviso': S('Aviso', fontName='Helvetica', fontSize=9, leading=13, textColor=CINZA_SUAVE, alignment=TA_CENTER),
        'Celula': S('Celula', fontName='Helvetica', fontSize=13, leading=17, textColor=TEXTO),
        'CelulaNegrito': S('CelulaNegrito', fontName='Helvetica-Bold', fontSize=12.5, leading=16, textColor=CINZA_SUAVE),
        'CelulaCab': S('CelulaCab', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=OURO, alignment=TA_CENTER),
        'ItemOuro': item('ItemOuro', OURO),
        'ItemVerde': item('ItemVerde', VERDE_CLARO),
        'ItemLaranja': item('ItemLaranja', LARANJA_CLARO),
    }


def cabecalho_secao(est, titulo, largura=LARGURA):
    t = Table([[Paragraph(escape(titulo).upper(), est['TituloSecao'])]], colWidths=[largura])
    t.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 1.6, OURO),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
    ]))
    return t


def secao(est, titulo, cartoes, gap=12):
    """Título da seção + cartões. O título sempre fica junto do primeiro cartão."""
    saida = [KeepTogether([cabecalho_secao(est, titulo), Spacer(1, 14), cartoes[0]])]
    for c in cartoes[1:]:
        saida += [Spacer(1, gap), c]
    saida.append(Spacer(1, 30))
    return saida


def abreviar_nome(nome, limite=16):
    nome = " ".join(str(nome).split()) or "Pessoa"
    if len(nome) > limite:
        nome = nome.split()[0]
    return nome[:limite]

def gerar_pdf_mapa_por_signos(nome1, signo1, nome2, signo2, email):
    s1, s2 = signo1, signo2
    d1, d2 = SIGNOS[s1], SIGNOS[s2]
    analise = obter_analise_exclusiva(s1, s2)
    geral, scores = calcular_scores(s1, s2)

    nome1_original, nome2_original = nome1, nome2
    nome1, nome2 = abreviar_nome(nome1), abreviar_nome(nome2)
    n1, n2 = escape(nome1), escape(nome2)

    nome_seguro = re.sub(r'[^\w\-]+', '_', f"{nome1_original}_e_{nome2_original}", flags=re.UNICODE).strip('_')
    filename = f"Mapa_Astral_Casal_{nome_seguro}.pdf"
    filepath = os.path.join(PDF_DIR, filename)

    ctx = dict(nome1=nome1, nome2=nome2, s1=s1, s2=s2, geral=geral, tagline=analise["tagline"])

    doc = BaseDocTemplate(
        filepath, pagesize=(W, H),
        title="Mapa Astral do Casal", author="Mapa Astral do Casal",
        leftMargin=MARGEM, rightMargin=MARGEM, topMargin=46, bottomMargin=46,
    )
    frame_capa = Frame(MARGEM, 40, LARGURA, 20, id='capa', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    frame_cont = Frame(MARGEM, 46, LARGURA, HC - 46 - 46, id='cont', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([
        PageTemplate(id='capa', frames=[frame_capa], pagesize=(W, H), onPage=lambda c, d: desenhar_capa(c, d, ctx)),
        PageTemplate(id='conteudo', frames=[frame_cont], pagesize=(W, HC), onPage=lambda c, d: desenhar_pagina(c, d, ctx)),
    ])

    est = criar_estilos()
    CW = LARGURA - 32  # largura útil dentro de um cartão

    def caixa(itens, **kw):
        return CaixaArredondada(itens, LARGURA, **kw)

    def P(txt, estilo):
        return Paragraph(txt, est[estilo])

    story = [Spacer(1, 1), NextPageTemplate('conteudo'), PageBreak()]

    # ---------- Compatibilidade geral ----------
    def cartao_signo(nome, signo, d):
        return caixa([
            P(nome.upper(), 'Eyebrow'),
            P(signo, 'NomeCard'),
            Spacer(1, 4),
            P(f"{d['elem']} · {d['mod']} · Regente {d['planeta']}", 'Sutil'),
        ])
    story += secao(est, "Compatibilidade geral", [cartao_signo(n1, s1, d1), cartao_signo(n2, s2, d2)])

    # ---------- Termômetro ----------
    i_max, i_min = scores.index(max(scores)), scores.index(min(scores))
    barras = []
    for i, (rotulo, valor) in enumerate(zip(CATEGORIAS, scores)):
        barras.append(BarraCompat(rotulo, valor, CW, destaque=(i == i_max)))
        barras.append(Spacer(1, 6))
    nota_alta = CaixaArredondada(
        [P("MAIOR DESTAQUE", 'NotaRotulo'), P(f"{escape(CATEGORIAS[i_max])} ({scores[i_max]}%)", 'NotaTexto')],
        CW, fundo=CREME, borda=OURO_BORDA, raio=10, pad_x=14, pad_y=11)
    nota_baixa = CaixaArredondada(
        [P("MERECE MAIS CARINHO", 'NotaRotulo'), P(f"{escape(CATEGORIAS[i_min])} ({scores[i_min]}%)", 'NotaTexto')],
        CW, fundo=LILAS_FUNDO, borda=LILAS_CLARO, raio=10, pad_x=14, pad_y=11)
    story += secao(est, "Termômetro da relação",
                   [caixa(barras + [Spacer(1, 8), nota_alta, Spacer(1, 10), nota_baixa])])

    # ---------- Palavras-chave ----------
    def bloco_chips(nome, d):
        return [P(nome, 'NomeCard'), Spacer(1, 8), Pilulas(d["kw"].split(" · "), CW)]
    story += secao(est, "Palavras-chave do casal",
                   [caixa(bloco_chips(n1, d1) + [Spacer(1, 18)] + bloco_chips(n2, d2))])

    # ---------- Dinâmica ----------
    story += secao(est, "A dinâmica energética do casal", [
        caixa([P("VISÃO GERAL DA CONEXÃO", 'Eyebrow'), P(analise["dinamica"], 'Corpo')])])

    # ---------- Elementos ----------
    def cartao_elemento(elem, dono):
        texto = [P(f"{elem} &nbsp;<font color='#6B6384' size='11'>· {dono}</font>", 'Titulo3'),
                 Spacer(1, 3), P(ELEMENTOS[elem], 'Corpo')]
        t = Table([[IconeElemento(elem), texto]], colWidths=[60, CW - 60])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        return caixa([t])
    story += secao(est, "Os elementos de vocês",
                   [cartao_elemento(d1["elem"], n1), cartao_elemento(d2["elem"], n2)])

    # ---------- Planetas ----------
    def cartao_planeta(planeta, signo):
        return caixa([
            P(f"{planeta} &nbsp;<font color='#6B6384' size='11'>· regente de {signo}</font>", 'Titulo3'),
            Spacer(1, 4), P(PLANETAS[planeta], 'Corpo'),
        ], fundo=LILAS_FUNDO)
    story += secao(est, "Os planetas que governam o amor de vocês",
                   [cartao_planeta(d1["planeta"], s1), cartao_planeta(d2["planeta"], s2)])

    # ---------- Ritmo ----------
    story += secao(est, "O ritmo da relação", [
        caixa([P(f"{d1['mod']} + {d2['mod']}".upper(), 'EyebrowOuro'), P(analise["ritmo"], 'CorpoEscuro')],
              fundo=ROXO_PROFUNDO, borda=OURO, espessura=1.6)])

    # ---------- Programas ----------
    itens_prog = [Paragraph(escape(i), est['ItemOuro'], bulletText='•') for i in analise["ideias"]]
    story += secao(est, "Programas ideais para o casal", [caixa(itens_prog, fundo=LILAS_FUNDO, pad_y=14)])

    # ---------- Amor na prática ----------
    story += secao(est, "O amor na prática", [
        caixa([P("AMOR & ROMANCE", 'Eyebrow'), P(analise["amor"], 'Corpo')]),
        caixa([P("COMUNICAÇÃO & ENTENDIMENTO", 'Eyebrow'), P(analise["comunicacao"], 'Corpo')]),
        caixa([P("QUÍMICA & INTIMIDADE", 'Eyebrow'), P(analise["intimidade"], 'Corpo')]),
    ])

    # ---------- Pontos fortes e de atenção ----------
    fortes = [P("Pontos fortes", 'TituloVerde')] + \
             [Paragraph(escape(i), est['ItemVerde'], bulletText='•') for i in analise["fortes"]]
    atencao = [P("Pontos de atenção", 'TituloLaranja')] + \
              [Paragraph(escape(i), est['ItemLaranja'], bulletText='•') for i in analise["atritos"]]
    story += secao(est, "Pontos fortes e pontos de atenção", [caixa(fortes), caixa(atencao)])

    # ---------- Jornada ----------
    etapas = [(n, fase, txt) for n, (fase, txt) in
              enumerate(zip(["Início", "Consolidação", "Longo prazo"], analise["jornada"]), 1)]
    story += secao(est, "A jornada do casal", [caixa([Jornada(etapas, CW, est)])])

    # ---------- Jeito de amar ----------
    def perfil_amor(nome, signo, d):
        def par(termo, texto):
            return [P(termo.upper(), 'Termo'), P(cap1(texto), 'Corpo'), Spacer(1, 10)]
        return caixa([
            P(nome.upper(), 'Eyebrow'), P(signo, 'NomeCard'), Spacer(1, 8),
            P(d["perfil"], 'Corpo'), Spacer(1, 12),
        ] + par("Linguagem do amor", d["ling"]) + par("Precisa de", d["precisa"]) +
            par("Ponto de atenção", d["cuidado"]) + [Spacer(1, 2), Pilulas(d["kw"].split(" · "), CW)])
    story += secao(est, "O jeito de amar de cada um", [perfil_amor(n1, s1, d1), perfil_amor(n2, s2, d2)])

    # ---------- Como amar melhor ----------
    def como_amar(nome, outro, d_outro, d_proprio):
        return caixa([
            P(f"PARA {nome.upper()}", 'Eyebrow'),
            P(f"Para conquistar o coração de {outro}, invista em {d_outro['ling']}", 'Corpo'),
            Spacer(1, 10),
            P(f"Seu ponto sensível: {d_proprio['cuidado']}", 'Sutil'),
        ], fundo=LILAS_FUNDO)
    story += secao(est, "Como amar melhor",
                   [como_amar(n1, n2, d2, d1), como_amar(n2, n1, d1, d2)])

    # ---------- Cores, pedras e números ----------
    linhas = [
        [Paragraph("", est['Celula']), Paragraph(n1, est['CelulaCab']), Paragraph(n2, est['CelulaCab'])],
        [P("Cor da sorte", 'CelulaNegrito'), P(d1["cor"], 'Celula'), P(d2["cor"], 'Celula')],
        [P("Pedra protetora", 'CelulaNegrito'), P(d1["pedra"], 'Celula'), P(d2["pedra"], 'Celula')],
        [P("Dia de energia", 'CelulaNegrito'), P(d1["dia"], 'Celula'), P(d2["dia"], 'Celula')],
        [P("Números", 'CelulaNegrito'), P(d1["nums"], 'Celula'), P(d2["nums"], 'Celula')],
    ]
    tq = Table(linhas, colWidths=[110, (LARGURA - 110) / 2, (LARGURA - 110) / 2])
    tq.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ROXO_PROFUNDO),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LILAS_FUNDO]),
        ('BOX', (0, 0), (-1, -1), 1, OURO),
        ('LINEBELOW', (0, 1), (-1, -2), 0.5, LILAS_CLARO),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story += secao(est, "Cores, pedras e números da sorte", [tq])

    # ---------- Ritual ----------
    dias = [CartaoDia(i, t, cap1(x), LARGURA, est) for i, (t, x) in enumerate(RITUAL, 1)]
    story += secao(est, "Ritual de 7 dias para fortalecer o vínculo", dias, gap=10)

    # ---------- Veredito ----------
    veredito = caixa([
        P("O CONSELHO DAS ESTRELAS PARA VOCÊS", 'EyebrowCentro'),
        P(analise["conselho"], 'Mensagem'),
        Spacer(1, 16),
        P("Que este mapa seja um convite para se conhecerem ainda mais. "
          "As estrelas apontam tendências, mas a história de vocês é escrita todos os dias, "
          "com escolhas, carinho e presença.", 'CorpoCentro'),
    ], fundo=ROXO_PROFUNDO, borda=OURO, espessura=1.2, pad_x=20, pad_y=24)
    story += [KeepTogether([
        cabecalho_secao(est, "Guia de harmonização & veredito"), Spacer(1, 14), veredito,
        Spacer(1, 22),
        P("Conteúdo de caráter simbólico e de entretenimento, baseado nos signos solares do casal.", 'Aviso'),
    ])]

    doc.build(story)
    return filename



# ==========================================
# 4. ROTAS DO FLASK (INTERFACE E GERAÇÃO)
# ==========================================

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
    
    filename = gerar_pdf_mapa_por_signos(nome1, signo1, nome2, signo2, email)
    
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
