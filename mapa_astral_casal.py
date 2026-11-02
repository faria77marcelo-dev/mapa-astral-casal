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

W, H = letter
MARGEM = 48
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
# 2. COMPONENTES VISUAIS E DECORAÇÃO
# ==========================================

class Medidor(Flowable):
    def __init__(self, score, size=132):
        super().__init__()
        self.score = score
        self.size = size
        self.width = size
        self.height = size
        self.hAlign = 'CENTER'

    def draw(self):
        c = self.canv
        cx = cy = self.size / 2
        r = self.size / 2 - 9
        c.setLineWidth(11)
        c.setLineCap(1)
        c.setStrokeColor(LILAS_CLARO)
        c.circle(cx, cy, r, stroke=1, fill=0)
        extensao = 3.6 * self.score
        c.setStrokeColor(ROXO_VIVO)
        c.arc(cx - r, cy - r, cx + r, cy + r, 90 - extensao, extensao)
        ang = math.radians(90 - extensao)
        c.setFillColor(OURO)
        c.circle(cx + r * math.cos(ang), cy + r * math.sin(ang), 6, stroke=0, fill=1)
        c.setFillColor(ROXO_PROFUNDO)
        c.setFont("Times-Bold", 34)
        c.drawCentredString(cx, cy - 7, f"{self.score}%")
        c.setFont("Helvetica", 7)
        c.setFillColor(OURO_ESCURO)
        c.drawCentredString(cx, cy - 22, "AFINIDADE")


class BarraCompat(Flowable):
    def __init__(self, rotulo, valor, largura):
        super().__init__()
        self.rotulo = rotulo
        self.valor = valor
        self.width = largura
        self.height = 30

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        w = self.width
        c.setFillColor(ROXO_PROFUNDO)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(0, 19, self.rotulo)
        c.setFillColor(OURO_ESCURO)
        c.drawRightString(w, 19, f"{self.valor}%")
        c.setFillColor(LILAS_CLARO)
        c.roundRect(0, 4, w, 8, 4, stroke=0, fill=1)
        c.setFillColor(ROXO_VIVO)
        largura_fill = max(10, w * self.valor / 100)
        c.roundRect(0, 4, largura_fill, 8, 4, stroke=0, fill=1)
        c.setFillColor(OURO)
        c.circle(largura_fill - 4, 8, 4.2, stroke=0, fill=1)


class IconeElemento(Flowable):
    CORES = {
        "Fogo": colors.HexColor('#F97316'),
        "Terra": colors.HexColor('#65A30D'),
        "Ar": colors.HexColor('#0EA5E9'),
        "Água": colors.HexColor('#6366F1'),
    }

    def __init__(self, elem, size=38):
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
        c.setLineWidth(1.7)
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
    passos = 120
    topo = (0x15 / 255, 0x07 / 255, 0x26 / 255)
    base = (0x45 / 255, 0x1A / 255, 0x8C / 255)
    for i in range(passos):
        t = i / (passos - 1)
        canvas.setFillColorRGB(*[topo[k] + (base[k] - topo[k]) * t for k in range(3)])
        canvas.rect(0, H - (i + 1) * H / passos, W, H / passos + 1, stroke=0, fill=1)

    cx, cy = W / 2, 405
    for raio, alfa in [(330, 0.035), (285, 0.04), (245, 0.05)]:
        canvas.setFillColor(ROXO_VIVO)
        canvas.setFillAlpha(alfa)
        canvas.circle(cx, cy, raio, stroke=0, fill=1)
    canvas.setFillAlpha(1)

    rnd = random.Random(11)
    for _ in range(170):
        x, y = rnd.uniform(8, W - 8), rnd.uniform(8, H - 8)
        r = rnd.choice([0.5, 0.7, 0.9, 1.2, 1.6])
        canvas.setFillColor(rnd.choice([OURO, colors.white, LILAS]))
        canvas.setFillAlpha(rnd.choice([0.25, 0.4, 0.6, 0.8]))
        canvas.circle(x, y, r, stroke=0, fill=1)
    canvas.setFillAlpha(1)

    ornamento(canvas, W / 2, H - 62)
    texto_esp(canvas, W / 2, H - 100, "MAPA ASTRAL", "Helvetica-Bold", 36, colors.white, 8, 'center')
    texto_esp(canvas, W / 2, H - 130, "DO CASAL", "Helvetica", 17, OURO, 13, 'center')
    texto_esp(canvas, W / 2, H - 154, "UM OLHAR SOBRE A ENERGIA QUE UNE VOCÊS", "Helvetica", 7.5, LILAS, 2.6, 'center')

    r_out, r_mid, r_in = 200, 152, 136
    canvas.setFillColor(ROXO_NOITE)
    canvas.setFillAlpha(0.55)
    canvas.circle(cx, cy, r_out, stroke=0, fill=1)
    canvas.setFillAlpha(1)
    canvas.setStrokeColor(OURO)
    canvas.setLineWidth(1.5)
    canvas.circle(cx, cy, r_out, stroke=1, fill=0)
    canvas.setLineWidth(0.8)
    canvas.circle(cx, cy, r_mid, stroke=1, fill=0)
    canvas.setStrokeColor(LILAS)
    canvas.setLineWidth(0.5)
    canvas.setStrokeAlpha(0.5)
    canvas.circle(cx, cy, r_in, stroke=1, fill=0)
    canvas.circle(cx, cy, r_in - 22, stroke=1, fill=0)
    canvas.setStrokeAlpha(1)

    canvas.setStrokeColor(OURO)
    canvas.setLineWidth(0.6)
    canvas.setStrokeAlpha(0.7)
    for i in range(12):
        ang = math.radians(90 - i * 30)
        canvas.line(cx + r_mid * math.cos(ang), cy + r_mid * math.sin(ang),
                    cx + r_out * math.cos(ang), cy + r_out * math.sin(ang))
    canvas.setStrokeAlpha(1)

    nomes_signos = [n for n, _ in ZODIACO]
    idx_casal = [nomes_signos.index(ctx["s1"]), nomes_signos.index(ctx["s2"])]
    r_simb = (r_mid + r_out) / 2
    for i, (nome, simb) in enumerate(ZODIACO):
        ang = math.radians(75 - i * 30)
        x, y = cx + r_simb * math.cos(ang), cy + r_simb * math.sin(ang)
        destaque = i in idx_casal
        if destaque:
            canvas.setFillColor(OURO)
            canvas.circle(x, y, 19, stroke=0, fill=1)
        canvas.setFillColor(ROXO_NOITE if destaque else LILAS_CLARO)
        if FONTE_SIMBOLOS:
            canvas.setFont(FONTE_SIMBOLOS, 24)
            canvas.drawCentredString(x, y - 8.5, simb)
        else:
            canvas.setFont("Helvetica-Bold", 7)
            canvas.drawCentredString(x, y - 2.5, nome[:3].upper())

    if idx_casal[0] != idx_casal[1]:
        pts = []
        for i in idx_casal:
            ang = math.radians(75 - i * 30)
            pts.append((cx + r_in * math.cos(ang), cy + r_in * math.sin(ang)))
        canvas.setStrokeColor(OURO)
        canvas.setLineWidth(1)
        canvas.setStrokeAlpha(0.75)
        canvas.line(pts[0][0], pts[0][1], pts[1][0], pts[1][1])
        canvas.setStrokeAlpha(1)
    for i in set(idx_casal):
        ang = math.radians(75 - i * 30)
        canvas.setFillColor(OURO)
        canvas.circle(cx + r_in * math.cos(ang), cy + r_in * math.sin(ang), 4, stroke=0, fill=1)

    for nome, dy in [(ctx["nome1"], 36), (ctx["nome2"], -52)]:
        tam = ajustar_fonte(nome, "Times-Bold", 30, 170)
        canvas.setFont("Times-Bold", tam)
        canvas.setFillColor(colors.white)
        canvas.drawCentredString(cx, cy + dy, nome)
    canvas.setFillColor(OURO)
    if FONTE_SIMBOLOS:
        canvas.setFont(FONTE_SIMBOLOS, 22)
        canvas.drawCentredString(cx, cy - 9, "♥")
    else:
        canvas.setFont("Times-Bold", 24)
        canvas.drawCentredString(cx, cy - 9, "&")

    canvas.setFont("Times-Bold", 50)
    canvas.setFillColor(OURO)
    canvas.drawCentredString(W / 2, 148, f"{ctx['geral']}%")
    texto_esp(canvas, W / 2, 128, "AFINIDADE ASTRAL", "Helvetica", 8.5, LILAS_CLARO, 4.5, 'center')
    ornamento(canvas, W / 2, 112, 60)

    canvas.setFont("Times-Italic", 16)
    canvas.setFillColor(colors.white)
    canvas.drawCentredString(W / 2, 88, ctx["tagline"])

    f_s = FONTE_SIMBOLOS or "Helvetica"
    texto_misto(canvas, W / 2, 56, [
        (ctx["simb1"] + " " if FONTE_SIMBOLOS else "", f_s, 13, OURO),
        (ctx["s1"].upper(), "Helvetica-Bold", 9, LILAS_CLARO),
        ("     ✦     " if FONTE_SIMBOLOS else "     •     ", f_s if FONTE_SIMBOLOS else "Helvetica", 9, OURO),
        (ctx["simb2"] + " " if FONTE_SIMBOLOS else "", f_s, 13, OURO),
        (ctx["s2"].upper(), "Helvetica-Bold", 9, LILAS_CLARO),
    ])
    texto_esp(canvas, W / 2, 30, f"GERADO EM {datetime.now().strftime('%d/%m/%Y')}", "Helvetica", 7, LILAS, 2, 'center')
    canvas.restoreState()


def desenhar_pagina(canvas, doc, ctx):
    canvas.saveState()
    canvas.setFillColor(FUNDO_PAGINA)
    canvas.rect(0, 0, W, H, stroke=0, fill=1)

    canvas.setFillColor(ROXO_PROFUNDO)
    canvas.rect(0, H - 40, W, 40, stroke=0, fill=1)
    canvas.setFillColor(OURO)
    canvas.rect(0, H - 43, W, 3, stroke=0, fill=1)
    texto_esp(canvas, MARGEM, H - 25, "MAPA ASTRAL DO CASAL", "Helvetica-Bold", 7.5, OURO, 3)
    canvas.setFont("Times-Italic", 10.5)
    canvas.setFillColor(LILAS_CLARO)
    canvas.drawRightString(W - MARGEM, H - 25, f"{ctx['nome1']} & {ctx['nome2']}")

    canvas.setStrokeColor(LILAS_CLARO)
    canvas.setLineWidth(0.8)
    canvas.line(MARGEM, 44, W - MARGEM, 44)
    canvas.setFillColor(OURO_ESCURO)
    if FONTE_SIMBOLOS:
        canvas.setFont(FONTE_SIMBOLOS, 9)
        canvas.drawCentredString(W / 2 - 20, 28, "✦")
        canvas.drawCentredString(W / 2 + 20, 28, "✦")
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawCentredString(W / 2, 28, str(canvas.getPageNumber()))
    texto_esp(canvas, MARGEM, 28, f"{ctx['s1'].upper()}  &  {ctx['s2'].upper()}", "Helvetica", 7, colors.HexColor('#8B80AA'), 2)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor('#8B80AA'))
    canvas.drawRightString(W - MARGEM, 28, datetime.now().strftime("%d/%m/%Y"))
    canvas.restoreState()


# ==========================================
# 3. ESTILOS E FUNÇÕES DE GERAÇÃO DO PDF
# ==========================================

def criar_estilos():
    base = getSampleStyleSheet()['Normal']
    def S(nome, **kw):
        return ParagraphStyle(nome, parent=base, **kw)
    return {
        'Corpo': S('Corpo', fontName='Helvetica', fontSize=10, leading=15.5, textColor=TEXTO, alignment=TA_JUSTIFY),
        'CorpoEscuro': S('CorpoEscuro', fontName='Helvetica', fontSize=10, leading=15.5, textColor=LILAS_CLARO, alignment=TA_JUSTIFY),
        'TituloCartao': S('TituloCartao', fontName='Helvetica-Bold', fontSize=9.5, leading=13, textColor=ROXO, spaceAfter=5),
        'TituloCartaoEscuro': S('TituloCartaoEscuro', fontName='Helvetica-Bold', fontSize=9.5, leading=13, textColor=OURO, spaceAfter=5),
        'TituloSecao': S('TituloSecao', fontName='Times-Bold', fontSize=15, leading=18, textColor=ROXO_PROFUNDO),
        'SimboloSecao': S('SimboloSecao', fontName='Helvetica', fontSize=15, leading=18),
        'Item': S('Item', fontName='Helvetica', fontSize=9.8, leading=14.5, textColor=TEXTO, leftIndent=13, firstLineIndent=-13, spaceAfter=4),
        'Pequeno': S('Pequeno', fontName='Helvetica', fontSize=8.5, leading=12.5, textColor=colors.HexColor('#6B6384')),
        'PequenoCentro': S('PequenoCentro', fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=OURO_ESCURO, alignment=TA_CENTER),
        'Citacao': S('Citacao', fontName='Times-Italic', fontSize=18, leading=24, textColor=OURO, alignment=TA_CENTER),
        'Nome': S('Nome', fontName='Times-Bold', fontSize=19, leading=22, textColor=colors.white, alignment=TA_CENTER),
        'Signo': S('Signo', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=LILAS, alignment=TA_CENTER),
        'SimboloGrande': S('SimboloGrande', fontName='Helvetica', fontSize=34, leading=40, alignment=TA_CENTER),
        'InfoCard': S('InfoCard', fontName='Helvetica', fontSize=8.5, leading=13, textColor=LILAS_CLARO, alignment=TA_CENTER),
        'Celula': S('Celula', fontName='Helvetica', fontSize=9.5, leading=13, textColor=TEXTO),
        'CelulaNegrito': S('CelulaNegrito', fontName='Helvetica-Bold', fontSize=9.5, leading=13, textColor=ROXO_PROFUNDO),
        'CelulaCab': S('CelulaCab', fontName='Helvetica-Bold', fontSize=9.5, leading=13, textColor=OURO, alignment=TA_CENTER),
        'Mensagem': S('Mensagem', fontName='Times-Italic', fontSize=13, leading=19, textColor=ROXO_PROFUNDO, alignment=TA_CENTER),
        'Aviso': S('Aviso', fontName='Helvetica', fontSize=7.5, leading=10.5, textColor=colors.HexColor('#8B80AA'), alignment=TA_CENTER),
        'Chip': S('Chip', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=ROXO, alignment=TA_CENTER),
        'ChipNome': S('ChipNome', fontName='Helvetica-Bold', fontSize=9.5, leading=12, textColor=OURO, alignment=TA_CENTER),
        'CorpoPeq': S('CorpoPeq', fontName='Helvetica', fontSize=9, leading=13.5, textColor=LILAS_CLARO),
        'NomeElem': S('NomeElem', fontName='Helvetica-Bold', fontSize=10.5, leading=13, textColor=ROXO_PROFUNDO),
        'DescElem': S('DescElem', fontName='Helvetica', fontSize=9, leading=13, textColor=TEXTO),
    }

def cabecalho_secao(est, simbolo, titulo, largura=LARGURA):
    marca = Paragraph(sym(simbolo, 15, HEX_OURO), est['SimboloSecao']) if simbolo else Paragraph("", est['SimboloSecao'])
    t = Table([[marca, Paragraph(escape(titulo).upper(), est['TituloSecao'])]], colWidths=[24, largura - 24])
    t.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, OURO),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    return t

def cartao(est, simbolo, titulo, texto, largura=LARGURA, escuro=False):
    marca = (sym(simbolo, 10, HEX_OURO if escuro else HEX_ROXO) + " &nbsp;") if simbolo else ""
    est_t = est['TituloCartaoEscuro'] if escuro else est['TituloCartao']
    est_c = est['CorpoEscuro'] if escuro else est['Corpo']
    conteudo = [Paragraph(marca + escape(titulo).upper(), est_t), Paragraph(texto, est_c)]
    t = Table([[conteudo]], colWidths=[largura])
    if escuro:
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), ROXO_PROFUNDO),
            ('BOX', (0, 0), (-1, -1), 0.8, OURO),
            ('LEFTPADDING', (0, 0), (-1, -1), 16), ('RIGHTPADDING', (0, 0), (-1, -1), 16),
            ('TOPPADDING', (0, 0), (-1, -1), 12), ('BOTTOMPADDING', (0, 0), (-1, -1), 13),
        ]))
    else:
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 0.6, LILAS_CLARO),
            ('LINEBEFORE', (0, 0), (0, -1), 4, ROXO_VIVO),
            ('LEFTPADDING', (0, 0), (-1, -1), 16), ('RIGHTPADDING', (0, 0), (-1, -1), 16),
            ('TOPPADDING', (0, 0), (-1, -1), 12), ('BOTTOMPADDING', (0, 0), (-1, -1), 13),
        ]))
    return t

def lista_itens(est, itens, simbolo, cor_hex):
    marca = sym(simbolo, 8, cor_hex) if simbolo else "•"
    return [Paragraph(f"{marca}&nbsp; {escape(i)}", est['Item']) for i in itens]

def abreviar_nome(nome, limite=16):
    nome = " ".join(str(nome).split()) or "Pessoa"
    if len(nome) > limite:
        nome = nome.split()[0]
    return nome[:limite]

def gerar_pdf_mapa_por_signos(nome1, signo1, nome2, signo2, email):
    s1, s2 = signo1, signo2
    simb1 = dict(ZODIACO).get(s1, "♈")
    simb2 = dict(ZODIACO).get(s2, "♉")
    d1, d2 = SIGNOS[s1], SIGNOS[s2]
    analise = obter_analise_exclusiva(s1, s2)
    geral, scores = calcular_scores(s1, s2)
    
    nome1_original, nome2_original = nome1, nome2
    nome1, nome2 = abreviar_nome(nome1), abreviar_nome(nome2)
    n1, n2 = escape(nome1), escape(nome2)

    nome_seguro = re.sub(r'[^\w\-]+', '_', f"{nome1_original}_e_{nome2_original}", flags=re.UNICODE).strip('_')
    filename = f"Mapa_Astral_Casal_{nome_seguro}.pdf"
    filepath = os.path.join(PDF_DIR, filename)

    ctx = dict(nome1=nome1, nome2=nome2, s1=s1, s2=s2, simb1=simb1, simb2=simb2,
               geral=geral, tagline=analise["tagline"])

    doc = BaseDocTemplate(
        filepath, pagesize=letter,
        title="Mapa Astral do Casal", author="Mapa Astral do Casal",
        leftMargin=MARGEM, rightMargin=MARGEM, topMargin=62, bottomMargin=58,
    )
    frame_capa = Frame(MARGEM, 40, LARGURA, 60, id='capa', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    frame_cont = Frame(MARGEM, 58, LARGURA, H - 58 - 64, id='cont', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([
        PageTemplate(id='capa', frames=[frame_capa], onPage=lambda c, d: desenhar_capa(c, d, ctx)),
        PageTemplate(id='conteudo', frames=[frame_cont], onPage=lambda c, d: desenhar_pagina(c, d, ctx)),
    ])

    est = criar_estilos()
    story = [Spacer(1, 1), NextPageTemplate('conteudo'), PageBreak()]
    GAP = 14
    METADE = (LARGURA - 12) / 2

    # PÁGINA 2
    def cartao_pessoa(nome, signo, simb, d):
        itens = []
        if FONTE_SIMBOLOS:
            itens.append(Paragraph(sym(simb, 36, HEX_OURO), est['SimboloGrande']))
        itens.append(Paragraph(nome, est['Nome']))
        itens.append(Paragraph(signo.upper(), est['Signo']))
        itens.append(Spacer(1, 8))
        info = (f"<font color='{HEX_LILAS}'>ELEMENTO</font> &nbsp;<b>{d['elem']}</b><br/>"
                f"<font color='{HEX_LILAS}'>MODALIDADE</font> &nbsp;<b>{d['mod']}</b><br/>"
                f"<font color='{HEX_LILAS}'>REGENTE</font> &nbsp;{sym(d['psimb'], 9, HEX_OURO)} <b>{d['planeta']}</b>")
        itens.append(Paragraph(info, est['InfoCard']))
        return itens

    gauge = [Medidor(geral), Spacer(1, 3), Paragraph("COMPATIBILIDADE GERAL", est['PequenoCentro'])]
    casal = Table([[cartao_pessoa(n1, s1, simb1, d1), gauge, cartao_pessoa(n2, s2, simb2, d2)]],
                  colWidths=[172, 172, 172])
    casal.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), ROXO_PROFUNDO),
        ('BACKGROUND', (2, 0), (2, 0), ROXO_PROFUNDO),
        ('BACKGROUND', (1, 0), (1, 0), LILAS_FUNDO),
        ('BOX', (0, 0), (-1, -1), 1, OURO),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 12), ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(casal)
    story.append(Spacer(1, GAP))

    frase = Table([[Paragraph(f"{sym('✦', 12, HEX_LILAS)} &nbsp;{escape(analise['tagline'])}&nbsp; {sym('✦', 12, HEX_LILAS)}", est['Citacao'])]],
                  colWidths=[LARGURA])
    frase.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), ROXO_PROFUNDO),
        ('LINEABOVE', (0, 0), (-1, 0), 2, OURO), ('LINEBELOW', (0, 0), (-1, 0), 2, OURO),
        ('TOPPADDING', (0, 0), (-1, -1), 12), ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
    ]))
    story.append(frase)
    story.append(Spacer(1, 14))

    story.append(cabecalho_secao(est, "♥", "Termômetro da Relação"))
    story.append(Spacer(1, 12))
    for rotulo, valor in zip(CATEGORIAS, scores):
        story.append(BarraCompat(rotulo, valor, LARGURA))
        story.append(Spacer(1, 2))

    i_max, i_min = scores.index(max(scores)), scores.index(min(scores))
    destaque = (f"<b>Maior destaque:</b> {escape(CATEGORIAS[i_max])} ({scores[i_max]}%) &nbsp;&nbsp;{sym('✦', 8, HEX_OURO)}&nbsp;&nbsp; "
                f"<b>Merece mais carinho:</b> {escape(CATEGORIAS[i_min])} ({scores[i_min]}%)")
    story.append(Spacer(1, 2))
    box = Table([[Paragraph(destaque, est['Celula'])]], colWidths=[LARGURA])
    box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CREME), ('BOX', (0, 0), (-1, -1), 0.6, OURO),
        ('LEFTPADDING', (0, 0), (-1, -1), 14), ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('TOPPADDING', (0, 0), (-1, -1), 9), ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(box)
    story.append(Spacer(1, 14))

    story.append(cabecalho_secao(est, "✦", "Palavras-Chave do Casal"))
    story.append(Spacer(1, 10))

    def linha_chips(nome, d):
        return [Paragraph(nome, est['ChipNome'])] + [Paragraph(escape(k), est['Chip']) for k in d["kw"].split(" · ")]

    tc = Table([linha_chips(n1, d1), linha_chips(n2, d2)], colWidths=[116, 133, 133, 134])
    tc.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), ROXO_PROFUNDO),
        ('BACKGROUND', (1, 0), (-1, -1), LILAS_FUNDO),
        ('INNERGRID', (1, 0), (-1, -1), 4, FUNDO_PAGINA),
        ('LINEAFTER', (0, 0), (0, -1), 4, FUNDO_PAGINA),
        ('LINEBELOW', (0, 0), (0, 0), 4, FUNDO_PAGINA),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 9), ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
    ]))
    story.append(tc)
    story.append(PageBreak())

    # PÁGINA 3
    story.append(cabecalho_secao(est, "☽", "A Dinâmica Energética do Casal"))
    story.append(Spacer(1, 10))
    story.append(cartao(est, "✦", "Visão geral da conexão", analise["dinamica"]))
    story.append(Spacer(1, 18))

    def cartao_elemento(elem, dono):
        conteudo = [Paragraph(f"{elem} &nbsp;<font color='#8B80AA' size='8'>· {escape(dono)}</font>", est['NomeElem']),
                    Spacer(1, 2), Paragraph(ELEMENTOS[elem], est['DescElem'])]
        t = Table([[IconeElemento(elem), conteudo]], colWidths=[46, METADE - 46])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white), ('BOX', (0, 0), (-1, -1), 0.6, LILAS_CLARO),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (0, 0), 9), ('LEFTPADDING', (1, 0), (1, 0), 4), ('RIGHTPADDING', (1, 0), (1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        return t

    def duas_colunas(a, b):
        t = Table([[a, "", b]], colWidths=[METADE, 12, METADE])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        return t

    story.append(cabecalho_secao(est, "▲", "Os Elementos de Vocês"))
    story.append(Spacer(1, 10))
    story.append(duas_colunas(cartao_elemento(d1["elem"], nome1), cartao_elemento(d2["elem"], nome2)))
    story.append(Spacer(1, 18))

    def cartao_planeta(planeta, psimb, signo, dono):
        titulo = Paragraph(f"{sym(psimb, 13, HEX_OURO)} &nbsp;{planeta} &nbsp;<font color='#8B80AA' size='8'>· regente de {signo}</font>", est['NomeElem'])
        conteudo = [titulo, Spacer(1, 3), Paragraph(PLANETAS[planeta], est['DescElem'])]
        t = Table([[conteudo]], colWidths=[METADE])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LILAS_FUNDO), ('BOX', (0, 0), (-1, -1), 0.6, LILAS_CLARO),
            ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 11),
        ]))
        return t

    story.append(cabecalho_secao(est, "♃", "Os Planetas que Governam o Amor de Vocês"))
    story.append(Spacer(1, 10))
    story.append(duas_colunas(cartao_planeta(d1["planeta"], d1["psimb"], s1, nome1),
                              cartao_planeta(d2["planeta"], d2["psimb"], s2, nome2)))
    story.append(Spacer(1, 18))

    story.append(cabecalho_secao(est, "♄", "O Ritmo da Relação"))
    story.append(Spacer(1, 10))
    story.append(cartao(est, "✦", f"{d1['mod']} + {d2['mod']}", analise["ritmo"], escuro=True))
    story.append(Spacer(1, 18))
    story.append(cabecalho_secao(est, "✦", "Programas Ideais para o Casal"))
    story.append(Spacer(1, 10))
    ideias = Table([[lista_itens(est, analise["ideias"], "✦", HEX_OURO)]], colWidths=[LARGURA])
    ideias.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LILAS_FUNDO), ('BOX', (0, 0), (-1, -1), 0.6, LILAS_CLARO),
        ('LEFTPADDING', (0, 0), (-1, -1), 16), ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ('TOPPADDING', (0, 0), (-1, -1), 12), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(ideias)
    story.append(Spacer(1, 22))
    story.append(PageBreak())

    # PÁGINA 4
    story.append(cabecalho_secao(est, "♥", "O Amor na Prática"))
    story.append(Spacer(1, 10))
    story.append(cartao(est, "♥", "Amor & Romance", analise["amor"]))
    story.append(Spacer(1, 12))
    story.append(cartao(est, "☿", "Comunicação & Entendimento", analise["comunicacao"]))
    story.append(Spacer(1, 12))
    story.append(cartao(est, "♀", "Química & Intimidade", analise["intimidade"]))
    story.append(Spacer(1, 22))

    story.append(cabecalho_secao(est, "✦", "Pontos Fortes e Pontos de Atenção"))
    story.append(Spacer(1, 10))

    def coluna_lista(titulo, simbolo, cor_hex, itens):
        return [Paragraph(f"{sym(simbolo, 9, cor_hex)}&nbsp; {escape(titulo).upper()}", est['TituloCartao']),
                Spacer(1, 3)] + lista_itens(est, itens, simbolo, cor_hex)

    forte = coluna_lista("Pontos fortes", "✦", HEX_ROXO, analise["fortes"])
    atenc = coluna_lista("Pontos de atenção", "◆", HEX_OURO, analise["atritos"])
    tab = Table([[forte, "", atenc]], colWidths=[METADE, 12, METADE])
    tab.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), LILAS_FUNDO), ('BOX', (0, 0), (0, 0), 0.6, LILAS_CLARO),
        ('BACKGROUND', (2, 0), (2, 0), CREME), ('BOX', (2, 0), (2, 0), 0.6, colors.HexColor('#EADBA8')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 14), ('RIGHTPADDING', (0, 0), (0, 0), 12),
        ('LEFTPADDING', (2, 0), (2, 0), 14), ('RIGHTPADDING', (2, 0), (2, 0), 12),
        ('LEFTPADDING', (1, 0), (1, 0), 0), ('RIGHTPADDING', (1, 0), (1, 0), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 12), ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(tab)
    story.append(Spacer(1, 22))

    story.append(cabecalho_secao(est, "☉", "A Jornada do Casal"))
    story.append(Spacer(1, 10))
    L3 = (LARGURA - 24) / 3
    colunas_fase = []
    for n, (fase, txt) in enumerate(zip(["Início", "Consolidação", "Longo prazo"], analise["jornada"]), 1):
        colunas_fase.append([Paragraph(f"{n:02d} &nbsp;·&nbsp; {fase.upper()}", est['TituloCartaoEscuro']),
                             Paragraph(escape(txt), est['CorpoPeq'])])
    tj = Table([[colunas_fase[0], "", colunas_fase[1], "", colunas_fase[2]]], colWidths=[L3, 12, L3, 12, L3])
    tj.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), ROXO_PROFUNDO), ('BOX', (0, 0), (0, 0), 0.8, OURO),
        ('BACKGROUND', (2, 0), (2, 0), ROXO_PROFUNDO), ('BOX', (2, 0), (2, 0), 0.8, OURO),
        ('BACKGROUND', (4, 0), (4, 0), ROXO_PROFUNDO), ('BOX', (4, 0), (4, 0), 0.8, OURO),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (1, 0), (1, 0), 0), ('RIGHTPADDING', (1, 0), (1, 0), 0),
        ('LEFTPADDING', (3, 0), (3, 0), 0), ('RIGHTPADDING', (3, 0), (3, 0), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 12), ('BOTTOMPADDING', (0, 0), (-1, -1), 13),
    ]))
    story.append(tj)
    story.append(PageBreak())

    # PÁGINA 5
    story.append(cabecalho_secao(est, "☉", "O Jeito de Amar de Cada Um"))
    story.append(Spacer(1, 10))

    def perfil_amor(nome, signo, simb, d):
        esq = []
        if FONTE_SIMBOLOS:
            esq.append(Paragraph(sym(simb, 30, HEX_OURO), est['SimboloGrande']))
        esq.append(Paragraph(f"<font size='14'>{nome}</font>", est['Nome']))
        esq.append(Paragraph(signo.upper(), est['Signo']))
        dir_ = [
            Paragraph(d["perfil"], est['Corpo']),
            Spacer(1, 5),
            Paragraph(f"<b><font color='{HEX_ROXO}'>Linguagem do amor:</font></b> {d['ling']}", est['Celula']),
            Paragraph(f"<b><font color='{HEX_ROXO}'>Precisa de:</font></b> {d['precisa']}", est['Celula']),
            Paragraph(f"<b><font color='{HEX_ROXO}'>Ponto de atenção:</font></b> {d['cuidado']}", est['Celula']),
            Spacer(1, 3),
            Paragraph(f"{sym('✦', 8, HEX_OURO)} <font color='#8B80AA'>{d['kw']}</font>", est['Pequeno']),
        ]
        t = Table([[esq, dir_]], colWidths=[118, LARGURA - 118])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), ROXO_PROFUNDO), ('BACKGROUND', (1, 0), (1, 0), colors.white),
            ('BOX', (0, 0), (-1, -1), 0.8, OURO),
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'), ('VALIGN', (1, 0), (1, 0), 'TOP'),
            ('LEFTPADDING', (0, 0), (0, 0), 6), ('RIGHTPADDING', (0, 0), (0, 0), 6),
            ('LEFTPADDING', (1, 0), (1, 0), 16), ('RIGHTPADDING', (1, 0), (1, 0), 16),
            ('TOPPADDING', (0, 0), (-1, -1), 13), ('BOTTOMPADDING', (0, 0), (-1, -1), 13),
        ]))
        return t

    story.append(perfil_amor(n1, s1, simb1, d1))
    story.append(Spacer(1, 12))
    story.append(perfil_amor(n2, s2, simb2, d2))
    story.append(Spacer(1, 22))

    story.append(cabecalho_secao(est, "♥", "Como Amar Melhor"))
    story.append(Spacer(1, 10))
    story.append(duas_colunas(
        cartao(est, "", f"Para {nome1}",
               f"Para conquistar o coração de {n2}, invista em <b>{d2['ling']}</b><br/><br/>"
               f"<font color='#8B80AA'>Seu ponto sensível:</font> {d1['cuidado']}", METADE),
        cartao(est, "", f"Para {nome2}",
               f"Para conquistar o coração de {n1}, invista em <b>{d1['ling']}</b><br/><br/>"
               f"<font color='#8B80AA'>Seu ponto sensível:</font> {d2['cuidado']}", METADE),
    ))
    story.append(Spacer(1, 14))
    story.append(cabecalho_secao(est, "☉", "Cores, Pedras e Números da Sorte"))
    story.append(Spacer(1, 10))
    linhas = [
        [Paragraph("", est['Celula']), Paragraph(n1, est['CelulaCab']), Paragraph(n2, est['CelulaCab'])],
        [Paragraph("Cor da sorte", est['CelulaNegrito']), Paragraph(d1["cor"], est['Celula']), Paragraph(d2["cor"], est['Celula'])],
        [Paragraph("Pedra protetora", est['CelulaNegrito']), Paragraph(d1["pedra"], est['Celula']), Paragraph(d2["pedra"], est['Celula'])],
        [Paragraph("Dia de energia", est['CelulaNegrito']), Paragraph(d1["dia"], est['Celula']), Paragraph(d2["dia"], est['Celula'])],
        [Paragraph("Números", est['CelulaNegrito']), Paragraph(d1["nums"], est['Celula']), Paragraph(d2["nums"], est['Celula'])],
    ]
    tq = Table(linhas, colWidths=[132, (LARGURA - 132) / 2, (LARGURA - 132) / 2])
    tq.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ROXO_PROFUNDO),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LILAS_FUNDO]),
        ('BOX', (0, 0), (-1, -1), 0.8, OURO),
        ('LINEBELOW', (0, 1), (-1, -2), 0.4, LILAS_CLARO),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(tq)
    story.append(PageBreak())

    # PÁGINA 6
    story.append(cabecalho_secao(est, "☽", "Ritual de 7 Dias para Fortalecer o Vínculo"))
    story.append(Spacer(1, 10))
    linhas_ritual = [[Paragraph(f"DIA {i}", est['CelulaCab']),
                      Paragraph(f"<b>{t}:</b> {x}", est['Celula'])] for i, (t, x) in enumerate(RITUAL, 1)]
    tr = Table(linhas_ritual, colWidths=[64, LARGURA - 64])
    tr.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), ROXO_PROFUNDO),
        ('ROWBACKGROUNDS', (1, 0), (1, -1), [colors.white, LILAS_FUNDO]),
        ('BOX', (0, 0), (-1, -1), 0.8, OURO),
        ('LINEBELOW', (0, 0), (-1, -2), 0.4, LILAS_CLARO),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (1, 0), (1, -1), 14), ('RIGHTPADDING', (1, 0), (1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(tr)
    story.append(Spacer(1, 22))

    story.append(cabecalho_secao(est, "☽", "Guia de Harmonização & Veredito"))
    story.append(Spacer(1, 10))
    story.append(cartao(est, "✦", "O conselho das estrelas para vocês", f"<i>{analise['conselho']}</i>", escuro=True))
    story.append(Spacer(1, 22))

    final = Table([[[
        Paragraph(sym("✦ &nbsp;✦ &nbsp;✦", 10, HEX_OURO), est['SimboloGrande']),
        Paragraph("Que este mapa seja um convite para se conhecerem ainda mais. "
                  "As estrelas apontam tendências, mas a história de vocês é escrita todos os dias, "
                  "com escolhas, carinho e presença.", est['Mensagem']),
    ]]], colWidths=[LARGURA])
    final.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CREME), ('BOX', (0, 0), (-1, -1), 0.8, OURO),
        ('LEFTPADDING', (0, 0), (-1, -1), 36), ('RIGHTPADDING', (0, 0), (-1, -1), 36),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 18),
    ]))
    story.append(KeepTogether([final, Spacer(1, 10),
                               Paragraph("Conteúdo de caráter simbólico e de entretenimento, baseado nos signos solares do casal.", est['Aviso'])]))

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
