"""A fala deriva da legenda: o normalizador legenda -> texto falavel.

O audio da CP-004 nao tem roteiro proprio -- PROIBIDO cria-lo. O texto
narrado e o campo txt de cada legenda passado por aqui. "(Art. 10)" vira
"artigo dez", "CPF" vira "ce-pe-efe" soletrado, e a pontuacao que na tela
marca ritmo (quebra de linha, travessao) vira pausa que a voz entende.

Por que normalizar em vez de jogar a legenda crua no TTS: o modelo le
"(Art. 10)" como ruido ou como "art ponto dez" -- os dois erram de um jeito
que so aparece QUANDO SE OUVE, e revisar audio e mais caro do que revisar
texto. Aqui o erro e erro de texto: aparece no diff, e o teste pega.

O cardinais sao de proposito: o cidadao fala "artigo dez", o ordinal
("artigo decimo") fica no texto escrito. A mesma frase que a tela mostra,
dita como quem conta -- nao como quem promulga.

Cobertura parcial e honesta: o que esta aqui cobre o corpus vivido das
legendas dos filmes. Casos novos chegam com teste novo, nao com adivinhacao
antecipada -- o Sprint 2 exercita o normalizador de ponta a ponta ao dublar.
"""
import re

# ---- numeros por extenso ------------------------------------------------
# Ate 999.999.999: artigo de lei e contagem de incisos nao pedem mais, e
# escrever bilhoes aqui seria codigo sem cliente real.
_UNIDADES = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete",
             "oito", "nove", "dez", "onze", "doze", "treze", "quatorze",
             "quinze", "dezesseis", "dezessete", "dezoito", "dezenove"]
_DEZENAS = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta",
            "setenta", "oitenta", "noventa"]
_CENTENAS = ["", "cento", "duzentos", "trezentos", "quatrocentos",
             "quinhentos", "seiscentos", "setecentos", "oitocentos",
             "novecentos"]


def por_extenso(n) -> str:
    """Inteiro -> cardinal PT-BR. "Art. 10" -> "artigo dez", nao "decimo"."""
    n = int(n)
    if not 0 <= n <= 999_999_999:
        raise ValueError(f"numero fora do alcance da fala: {n}")
    if n < 20:
        return _UNIDADES[n]
    if n < 100:
        d, u = divmod(n, 10)
        return _DEZENAS[d] + (f" e {_UNIDADES[u]}" if u else "")
    if n == 100:
        return "cem"
    if n < 1000:
        c, r = divmod(n, 100)
        return _CENTENAS[c] + (f" e {por_extenso(r)}" if r else "")
    if n < 1_000_000:
        milhares, resto = divmod(n, 1000)
        mil = "mil" if milhares == 1 else f"{por_extenso(milhares)} mil"
        # "mil e cem", mas "mil duzentos": o "e" antes de centena redonda e
        # a fala corrente; do resto em diante, espaco.
        return mil + (f" e {por_extenso(resto)}" if 0 < resto <= 100
                      else (f" {por_extenso(resto)}" if resto else ""))
    milhoes, resto = divmod(n, 1_000_000)
    cabeca = "um milhão" if milhoes == 1 else f"{por_extenso(milhoes)} milhões"
    if not resto:
        return cabeca
    return cabeca + (f" e {por_extenso(resto)}" if resto < 100
                     else f" {por_extenso(resto)}")


# ---- siglas -------------------------------------------------------------
# Letras ditadas: o TTS nao adivinha que "ANPD" e sigla -- pode tentar ler
# como palavra e sair "anpede". Soletrar e deterministico.
_LETRAS = {"A": "a", "B": "bê", "C": "cê", "D": "dê", "E": "e", "F": "éfe",
           "G": "gê", "H": "agâ", "I": "i", "J": "jota", "K": "ká", "L": "éle",
           "M": "eme", "N": "ene", "O": "ô", "P": "pê", "Q": "quê", "R": "erre",
           "S": "esse", "T": "tê", "U": "u", "V": "vê", "W": "dáblio",
           "X": "xis", "Y": "ípsilon", "Z": "zê",
           "Á": "a", "À": "a", "Â": "a", "Ã": "a", "Ä": "a",
           "É": "e", "Ê": "e", "Í": "i", "Ó": "o", "Ô": "o", "Õ": "o",
           "Ú": "u", "Ü": "u", "Ç": "cê"}
_RX_SIGLA = re.compile(r"\b[A-ZÀ-Ü]{2,}\b")

# ---- citacao de artigo ---------------------------------------------------
# "(Art. 5)", "(Arts. 37 e 38)", "Art. 10" solto: a referencia que a tela
# mostra entre parenteses e FALADA, porque o audio nao tem selo clicavel --
# citar o numero e a unica forma do ouvinte saber onde esta na lei.
_RX_ART = re.compile(r"\(?\s*Arts?\.\s*((?:\d+[ºª]?\s*(?:e\b|,)\s*)*\d+[ºª]?)\s*\)?",
                     re.IGNORECASE)


def _cita_artigo(m):
    nums = re.findall(r"\d+", m.group(1))
    palavra = "artigo" if len(nums) == 1 else "artigos"
    return palavra + " " + " e ".join(por_extenso(x) for x in nums)


def normalizar(txt: str) -> str:
    """O txt de uma legenda -> o texto que a voz le.

    Um texto, quatro dobras: citacao de artigo vira fala, sigla vira
    soletração, numero vira cardinal, e a pontuacao de LEITOR (linha, traço)
    vira pontuacao de OUVINTE (pausa). O resto passa intacto -- acentos
    inclusive, que o TTS precisa deles.
    """
    t = txt.replace("\n", " ")                    # quebra de linha: a tela pula, a voz continua

    t = _RX_ART.sub(_cita_artigo, t)              # (Art. 5) -> artigo cinco

    t = _RX_SIGLA.sub(                            # CPF -> cê-pé-éfe
        lambda m: "-".join(_LETRAS.get(c, c.lower()) for c in m.group(0)), t)

    t = re.sub(r"(\d+)\s*%",                      # 70% -> setenta por cento
               lambda m: por_extenso(m.group(1)) + " por cento", t)
    t = re.sub(r"(\d+)[ºª]", r"\1", t)            # 9º -> 9 (o ordinal ja era do artigo)
    t = re.sub(r"\d+", lambda m: por_extenso(m.group(0)), t)

    t = t.replace("—", ",").replace("–", ",")     # travessão: pausa, nao silencio
    t = re.sub(r"\s+,", ",", t)
    t = re.sub(r",{2,}", ",", t)
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip(" ,").strip()


# O Narrador nao e rig -- e quem fala quando o plano nao tem guardiao nem
# "quem". Parametros de partida do Apendice A da CP-004: neutro e
# contrastante, para a troca de voz se OUVIR. Vive aqui, e nao num rig,
# porque narrador nao tem corpo.
NARRADOR = {"registro": "neutro, contrastante", "pitch": "médio", "ritmo": 0.0}
