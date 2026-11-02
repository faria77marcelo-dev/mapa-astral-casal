import os
import re
import math
import random
import threading
import time
import zlib
from datetime import datetime
from xml.sax.saxutils import escape

import requests
from flask import Flask, request, jsonify, render_template_string, send_file
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

# ==========================================
# 0. PALETA, FONTES E CONSTANTES
# ==========================================

W, H = letter
MARGEM = 48
LARGURA = W - 2 * MARGEM  # 516

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

def obter_signo_com_simbolo(dia, mes):
    if (mes == 3 and dia >= 21) or (mes == 4 and dia <= 19):
        return "Áries", "♈"
    elif (mes == 4 and dia >= 20) or (mes == 5 and dia <= 20):
        return "Touro", "♉"
    elif (mes == 5 and dia >= 21) or (mes == 6 and dia <= 20):
        return "Gêmeos", "♊"
    elif (mes == 6 and dia >= 21) or (mes == 7 and dia <= 22):
        return "Câncer", "♋"
    elif (mes == 7 and dia >= 23) or (mes == 8 and dia <= 22):
        return "Leão", "♌"
    elif (mes == 8 and dia >= 23) or (mes == 9 and dia <= 22):
        return "Virgem", "♍"
    elif (mes == 9 and dia >= 23) or (mes == 10 and dia <= 22):
        return "Libra", "♎"
    elif (mes == 10 and dia >= 23) or (mes == 11 and dia <= 21):
        return "Escorpião", "♏"
    elif (mes == 11 and dia >= 22) or (mes == 12 and dia <= 21):
        return "Sagitário", "♐"
    elif (mes == 12 and dia >= 22) or (mes == 1 and dia <= 19):
        return "Capricórnio", "♑"
    elif (mes == 1 and dia >= 20) or (mes == 2 and dia <= 18):
        return "Aquário", "♒"
    else:
        return "Peixes", "♓"


ZODIACO = [
    ("Áries", "♈"), ("Touro", "♉"), ("Gêmeos", "♊"), ("Câncer", "♋"),
    ("Leão", "♌"), ("Virgem", "♍"), ("Libra", "♎"), ("Escorpião", "♏"),
    ("Sagitário", "♐"), ("Capricórnio", "♑"), ("Aquário", "♒"), ("Peixes", "♓"),
]

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
        atritos=["Rotina que pode virar monotonia", "Te
