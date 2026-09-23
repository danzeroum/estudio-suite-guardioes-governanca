"""As seis etapas entre uma historia em prosa e um filme dubrado.

Cinco etapas nasceram com a suite; a sexta, `sonorizacao`, veio com a
CP-004 -- e e a unica que depende de ferramenta EXTERNA (a audio-suite,
chamada por CLI, nunca copiada). Por isso o mapeamento dela tem tres
estados de saida: 0 verde, 1 vermelho, e "nao consegui medir" vira
INDECISO -- porque "a audio-suite nao estava la" e "a trilha esta errada"
sao coisas diferentes, e colapsa-las faz a leitura barata vencer.

Cada etapa tem UM artefato revisavel e UM portao. O agente itera dentro da
etapa e nunca avanca com portao vermelho -- e a sequencia que de fato
funcionou nas sete fases do repositorio de origem, agora com nome e fiscal.

A ordem e cara de inverter, e e de proposito que a etapa `roteiro` nao tem uma
linha de codigo: errar o roteiro custa uma edicao de texto, errar depois custa
refilmagem. O erro dos "onze direitos do Art. 18" que chegou a ser publicado
nasceu exatamente de pular esse portao.

Portao que nao consegue decidir NAO devolve verde. Ele devolve `indeciso`, que
e um terceiro estado -- porque "o navegador nao estava disponivel" e "o filme
esta correto" sao coisas diferentes, e colapsa-las faz a leitura barata vencer.
"""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .comum import FILMES, HARNESS, RAIZ, dados_do_filme
from . import lei as _lei

ETAPAS = ["recepcao", "roteiro", "storyboard", "animacao", "acabamento",
          "sonorizacao"]


@dataclass
class Veredito:
    etapa: str
    estado: str                       # "verde" | "vermelho" | "indeciso"
    achados: list = field(default_factory=list)
    nota: str = ""
    # CP-008: a CAUSA do vermelho, num campo estruturado -- nunca em
    # busca de texto na nota. O portao de sonorizacao distingue
    # "promessa-quebrada" (ferramenta prometida e ausente: NADA foi
    # medido) de "trilha-reprovada" (FINDING da audio-suite: a trilha
    # foi medida e reprovou) e de "declaracao-divergente" (o filme
    # declara o que nao existe). Vermelho sem causa e vermelho sem
    # diagnostico, e quem le o log escolhe a correcao errada.
    causa: str = ""

    @property
    def ok(self):
        return self.estado == "verde"


def _v(etapa, achados, indeciso=False, nota=""):
    if indeciso:
        return Veredito(etapa, "indeciso", achados, nota)
    return Veredito(etapa, "vermelho" if achados else "verde", achados, nota)


# ---- recepcao --------------------------------------------------------------
# Os quatro campos sem os quais o roteiro vira chute -- e o chute so aparece
# no fim, quando ja custa refilmagem. O prefixo tolera marcacao de markdown
# ("- **Tema:**"), porque exigir formato puro faria o portao reprovar um pedido
# correto por causa de dois asteriscos: fiscal que reprova o certo e desligado.
_MARCA = r"[-*#>\s]*"
SECOES_PEDIDO = {
    "tema": rf"(?im)^{_MARCA}tema{_MARCA}[:\-]",
    "publico": rf"(?im)^{_MARCA}p[úu]blico{_MARCA}[:\-]",
    "duracao": rf"(?im)^{_MARCA}dura[çc][ãa]o{_MARCA}[:\-]",
    "aprendizado": rf"(?im)^{_MARCA}(o que se aprende|aprendizado|mensagem){_MARCA}[:\-]",
}


def portao_recepcao(fid):
    p = FILMES / fid / "pedido.md"
    if not p.exists():
        return _v("recepcao", [f"falta {p.relative_to(RAIZ)} — a historia como ela chegou"])
    txt = p.read_text(encoding="utf-8")
    faltam = [k for k, rx in SECOES_PEDIDO.items() if not re.search(rx, txt)]
    achados = []
    if faltam:
        achados.append(
            "o pedido nao diz: " + ", ".join(faltam) +
            ". Sem isso o roteiro vira chute, e o chute so aparece no fim.")
    if len(txt.split()) < 25:
        achados.append("o pedido tem menos de 25 palavras — curto demais para virar roteiro")
    return _v("recepcao", achados)


# ---- roteiro ---------------------------------------------------------------
def planos_da_prosa(fid):
    """(id, titulo, dur, artigos) de cada plano, lidos do roteiro em prosa."""
    md = (FILMES / fid / "roteiro.md")
    if not md.exists():
        return []
    out = []
    for m in re.finditer(r"^### (p\d\d) — (.+?) · (\d+) s ·(.*)$",
                         md.read_text(encoding="utf-8"), re.M):
        cauda = m.group(4)
        arts = re.findall(r"Art\.\s*(\d+)", cauda)
        out.append({"id": m.group(1), "titulo": m.group(2),
                    "dur": int(m.group(3)), "arts": [int(a) for a in arts],
                    "cauda": cauda})
    return out


def portao_roteiro(fid):
    """A prosa ja tem de citar artigo que existe, atribuido ao guardiao certo.

    Este portao roda ANTES de existir uma linha de dado. E onde a citacao
    errada custa uma edicao de texto em vez de uma refilmagem -- e a licao
    mais cara das sete fases.
    """
    md = FILMES / fid / "roteiro.md"
    if not md.exists():
        return _v("roteiro", [f"falta {md.relative_to(RAIZ)} — a prosa e a shot list"])
    try:
        arts, guardioes = _lei.carregar()
    except Exception as e:
        return _v("roteiro", [f"nao consegui ler a lei ancorada: {e}"], indeciso=True)

    planos = planos_da_prosa(fid)
    achados = []
    if not planos:
        achados.append("nenhum plano no formato '### pNN — titulo · N s · ...'")
    emoji = {"raposa": "🦊", "coruja": "🦉", "aguia": "🦅",
             "tartaruga": "🐢", "elefante": "🐘"}
    for P in planos:
        for a in P["arts"]:
            if str(a) not in arts:
                achados.append(f"{P['id']}: cita Art. {a}, que a lei ancorada nao tem")
                continue
            dono = arts[str(a)]["guardiao"]
            # O guardiao dono e o da FONTE, nunca o que esta em cena. Seguir a
            # intuicao narrativa ja produziu seis planos errados de uma vez.
            declarado = [g for g, e in emoji.items() if e in P["cauda"]]
            if declarado and dono not in declarado:
                achados.append(
                    f"{P['id']}: Art. {a} e de '{dono}', mas o plano anuncia "
                    f"'{declarado[0]}' — o dono vem da fonte canonica, nao de quem atua")
    if not any(P["arts"] for P in planos) and planos:
        achados.append("nenhum plano cita artigo — um filme dos Guardioes ensina a lei")
    return _v("roteiro", achados, nota=f"{len(planos)} plano(s) na prosa")


# ---- storyboard ------------------------------------------------------------
def fiscal_redublagem(fid):
    """O audio deriva da legenda E da camada de timbre; divida sem redublar.

    Mesmo espirito do "editar o filme sem regravar a referencia": audio.json
    carrega o sha256 do texto NORMALIZADO de cada legenda, os PARAMETROS de
    timbre aplicados (CP-005: portadora, mistura, bandas, sha da portadora)
    e a agenda de earcons do Dado. Quem edita o texto, o tempo, o timbre do
    rig ou os momentos do Dado sem rodar `dublar` deixa a divida aqui. Nao
    ha falso positivo: filme sem audio/ simplesmente nao e fiscalizado --
    a camada e aditiva, e o filme mudo continua valido por completo.
    """
    import hashlib
    import json
    from . import fala
    from .dublar import _earcons_do_filme, quem_fala

    manifesto = FILMES / fid / "audio" / "audio.json"
    if not manifesto.exists():
        return []
    d = dados_do_filme(fid)
    gravado = json.loads(manifesto.read_text(encoding="utf-8"))
    por_chave = {(c["plano"], round(c["em"], 3)): c for c in gravado.get("clipes", [])}

    # CP-007: o audio.json nasce com o ambiente que sintetizou (as versoes
    # efetivas, == voz.lock por construcao). Sem o campo, a dublagem e de
    # ambiente desconhecido; com ambiente divergente do lock, o audio
    # commitado nao e o que o lock reproduz -- as duas coisas sao divida,
    # e a divida se resolve com o mesmo comando das outras.
    from . import voz as _voz
    try:
        esperado_amb = _voz.ancora()["ambiente"]
    except Exception as e:
        esperado_amb = None
        achados_ambiente = [f"o voz.lock nao entrega o bloco ambiente ({e})"]
    else:
        gravado_amb = gravado.get("ambiente")
        if not gravado_amb:
            achados_ambiente = [
                f"audio.json sem o campo ambiente — dublagem de ambiente nao "
                f"ancorado (CP-007). Rode: python3 -m estudio_suite dublar {fid}"]
        elif gravado_amb != esperado_amb:
            detalhe = []
            for k in sorted(set(gravado_amb) | set(esperado_amb)):
                if gravado_amb.get(k) != esperado_amb.get(k):
                    detalhe.append(
                        f"{k}: {gravado_amb.get(k)} gravado, "
                        f"{esperado_amb.get(k)} no lock")
            achados_ambiente = [
                f"o ambiente da dublagem diverge do voz.lock ({'; '.join(detalhe)})"
                f". Rode: python3 -m estudio_suite dublar {fid}"]
        else:
            achados_ambiente = []

    from . import amostras as _am
    try:
        shas_de_lock = {k: v["sha256"] for k, v in _am.ancora().items()}
    except Exception:
        shas_de_lock = {}

    def _timbre_esperado(P, L):
        _t, _r, _rot, tim = quem_fala(P, L, d.get("elenco", {}))
        if not tim:
            return None
        return {
            "portadora": tim["portadora"],
            "mistura": float(tim["mistura"]),
            "bandas": int(tim.get("bandas", 16) or 16),
            "portadora_sha256": shas_de_lock.get(tim["portadora"], None),
        }

    achados = list(achados_ambiente)
    cursor = 0.0
    atuais = 0
    for P in d["planos"]:
        for L in P.get("legendas") or []:
            atuais += 1
            em = round(cursor + L["em"], 3)
            c = por_chave.get((P["id"], em))
            if c is None:
                achados.append(
                    f"{P['id']}: legenda em {em:.1f}s nao existe na dublagem — "
                    f"o audio foi mixado antes desta legenda. Rode: "
                    f"python3 -m estudio_suite dublar {fid}")
                continue
            if abs(c["ate"] - (cursor + L["ate"])) > 0.01:
                achados.append(
                    f"{P['id']}: legenda termina em {cursor + L['ate']:.1f}s, mas a "
                    f"dublagem gravou {c['ate']:.1f}s — o tempo mudou e o audio "
                    f"continua no tempo antigo. Rode: python3 -m estudio_suite dublar {fid}")
            texto = fala.normalizar(L["txt"])
            hash_atual = hashlib.sha256(texto.encode("utf-8")).hexdigest()
            if c["texto_sha256"] != hash_atual:
                achados.append(
                    f"{P['id']}: legenda {em:.1f}s mudou de texto desde a dublagem "
                    f"(sha256 diverge). Rode: python3 -m estudio_suite dublar {fid}")
            esperado = _timbre_esperado(P, L)
            gravado_tim = c.get("timbre")
            if esperado is None and gravado_tim:
                achados.append(
                    f"{P['id']}: legenda {em:.1f}s foi dublada COM timbre, mas o rig "
                    f"hoje nao declara (ou mistura 0) — o audio timbrado nao e mais "
                    f"o derivado. Rode: python3 -m estudio_suite dublar {fid}")
            elif esperado is not None and not gravado_tim:
                achados.append(
                    f"{P['id']}: legenda {em:.1f}s ganhou timbre no rig desde a "
                    f"dublagem (portadora '{esperado['portadora']}'). Rode: "
                    f"python3 -m estudio_suite dublar {fid}")
            elif esperado is not None and gravado_tim != esperado:
                detalhe = []
                for k in ("portadora", "mistura", "bandas"):
                    if gravado_tim.get(k) != esperado[k]:
                        detalhe.append(f"{k}: {gravado_tim.get(k)} -> {esperado[k]}")
                if gravado_tim.get("portadora_sha256") != esperado["portadora_sha256"]:
                    detalhe.append("portadora_sha256: o lock avancou")
                achados.append(
                    f"{P['id']}: legenda {em:.1f}s tem timbre divergente entre o rig "
                    f"e a dublagem ({'; '.join(detalhe)}). Rode: "
                    f"python3 -m estudio_suite dublar {fid}")
            # prosodia (CP-006): a expressao deriva do dado do filme; batida
            # que mudou sem redublar e a mesma divida das outras camadas.
            from .prosodia import expressao_da_fala, manifesto as _mpro
            esperado_pros = _mpro(expressao_da_fala(P, L, d.get("elenco", {})))
            gravado_pros = c.get("prosodia")
            if esperado_pros is None and gravado_pros:
                achados.append(
                    f"{P['id']}: legenda {em:.1f}s foi dublada COM prosodia "
                    f"({gravado_pros.get('expressao')}), mas a batida de expressao "
                    f"do falante nao existe mais no filme. Rode: "
                    f"python3 -m estudio_suite dublar {fid}")
            elif esperado_pros is not None and not gravado_pros:
                achados.append(
                    f"{P['id']}: legenda {em:.1f}s ganhou expressao "
                    f"'{esperado_pros['expressao']}' no filme desde a dublagem. "
                    f"Rode: python3 -m estudio_suite dublar {fid}")
            elif esperado_pros is not None and gravado_pros != esperado_pros:
                achados.append(
                    f"{P['id']}: legenda {em:.1f}s tem prosodia divergente entre o "
                    f"filme e a dublagem ({gravado_pros.get('expressao')} gravada, "
                    f"{esperado_pros['expressao']} esperada — ou o mapa em "
                    f"prosodia.py mudou). Rode: python3 -m estudio_suite dublar {fid}")
        cursor += P["dur"]

    gravados = len(gravado.get("clipes", []))
    if gravados > atuais:
        achados.append(
            f"a dublagem tem {gravados} clipe(s) para {atuais} legenda(s) — "
            f"legenda apagada sem redublar. Rode: python3 -m estudio_suite dublar {fid}")

    # A agenda de earcons deriva dos momentos do Dado no filme: mudou o
    # momento, mudou o carimbo -- sem redublar, o audio mente sobre o filme.
    esperados = {(p, em, t) for p, em, t in _earcons_do_filme(d)}
    gravados_ear = {(e["plano"], round(e["em"], 3), e["tipo"])
                    for e in gravado.get("earcons", [])}
    if esperados != gravados_ear:
        so_esperados = esperados - gravados_ear
        so_gravados = gravados_ear - esperados
        partes = []
        if so_esperados:
            partes.append("novo(s): " + ", ".join(
                f"{p}@{em:.1f}s/{t}" for p, em, t in sorted(so_esperados)))
        if so_gravados:
            partes.append("sobrando: " + ", ".join(
                f"{p}@{em:.1f}s/{t}" for p, em, t in sorted(so_gravados)))
        achados.append(
            f"os momentos do Dado mudaram sem redublar ({'; '.join(partes)}). "
            f"Rode: python3 -m estudio_suite dublar {fid}")
    return achados


def fiscal_amostras(fid):
    """Portadora de timbre em uso tem de estar ancorada no amostras.lock (CP-005).

    Som de terceiro sem ancora e pirataria em potencial -- e dublar com
    portadora "parecida" produziria um timbre que ninguem revisou. O fiscal
    ve o que o filme USA (o rig de quem fala em cada legenda) e confere se a
    portadora declarada no bloco voz.timbre do rig tem entrada no lock.
    Filme cujo elenco nao declara timbre simplesmente nao e fiscalizado --
    a camada e aditiva, e a CP-005 aplica timbre a nenhum filme ainda.
    """
    from . import amostras as _am
    from .dublar import voz_do_rig

    d = dados_do_filme(fid)
    rigs_em_uso = set()
    for P in d["planos"]:
        for L in P.get("legendas") or []:
            quem = L.get("quem")
            if quem:
                rig = (d.get("elenco", {}).get(quem) or {}).get("rig")
            else:
                rig = P.get("guardiao")
            if rig:
                rigs_em_uso.add(rig)

    declarados = {}
    for rig in sorted(rigs_em_uso):
        t = (voz_do_rig(rig) or {}).get("timbre") or {}
        if t.get("portadora"):
            declarados[rig] = t["portadora"]
    if not declarados:
        return []

    try:
        ancoradas = _am.ancora()
    except Exception as e:
        return [f"o elenco declara timbre, mas a ancora falhou: {e}"]

    achados = []
    for rig, portadora in sorted(declarados.items()):
        if portadora not in ancoradas:
            achados.append(
                f"{rig}: o bloco voz.timbre declara a portadora '{portadora}', "
                f"que NAO consta em amostras.lock -- som sem ancora e pirataria "
                f"em potencial. Ancore a portadora (lock + change-proposal, com "
                f"licenca verificada) ou remova o timbre do rig.")
    return achados


def portao_storyboard(fid):
    """O dado existe, e o validador completo passa sobre ele."""
    js = FILMES / fid / f"{fid}.filme.js"
    if not js.exists():
        return _v("storyboard", [f"falta {js.relative_to(RAIZ)} — o filme como dado"])
    # O validador completo, em silencio: a saida dele e para quem o chama
    # direto. Repeti-la aqui criaria duas versoes da mesma resposta, e a
    # resumida seria a que as pessoas citariam.
    import io
    from contextlib import redirect_stdout

    from . import roteiro as _rot
    antes, antes_n = list(_rot.falhas), _rot.checados
    _rot.falhas.clear()
    try:
        with redirect_stdout(io.StringIO()):
            _rot.main()
    except Exception as e:
        _rot.falhas.clear(); _rot.falhas.extend(antes); _rot.checados = antes_n
        return _v("storyboard", [f"o validador nao rodou: {e}"], indeciso=True)
    meus = [f for f in _rot.falhas if fid in f]
    outros = [f for f in _rot.falhas if fid not in f]
    _rot.falhas.clear(); _rot.falhas.extend(antes); _rot.checados = antes_n
    # A dublagem deriva do dado: se o dado mudou, o audio gravado e divida.
    meus += fiscal_redublagem(fid)
    # O timbre deriva de portadora de terceiros: sem entrada no lock, e divida
    # tambem -- e a divida que a CP-005 nao deixa ouvir (pirataria em potencial).
    meus += fiscal_amostras(fid)
    nota = f"{len(outros)} achado(s) em outros filmes" if outros else ""
    return _v("storyboard", meus, nota=nota)


# ---- animacao --------------------------------------------------------------
def portao_animacao(fid):
    d = dados_do_filme(fid)
    base = FILMES / fid / "baseline"
    refs = sorted(base.glob("*.txt"))
    achados = []
    if not refs:
        achados.append("nenhuma referencia de palco — rode: "
                       "python3 tests/test_navegador.py --gravar")
    elif len(refs) != len(d["planos"]):
        achados.append(f"{len(refs)} referencia(s) para {len(d['planos'])} plano(s)")
    if achados:
        return _v("animacao", achados)
    # Se as referencias BATEM e coisa do teste de navegador: aqui so se diz que
    # existem e sao tantas quanto os planos. Reimplementar a comparacao seria
    # uma segunda versao da mesma resposta.
    return _v("animacao", [], nota=f"{len(refs)} referencia(s); a comparacao e do "
                                   "teste de navegador")


# ---- acabamento ------------------------------------------------------------
def portao_acabamento(fid):
    rel = FILMES / fid / "relatorio.json"
    if not rel.exists():
        return _v("acabamento", [], indeciso=True,
                  nota="sem relatorio de execucao — rode o teste de navegador "
                       "para produzir a evidencia")
    import json
    d = json.loads(rel.read_text(encoding="utf-8"))
    achados = [f"{k}: {v}" for k, v in (d.get("achados") or {}).items()]
    return _v("acabamento", achados, nota=d.get("nota", ""))


# ---- sonorizacao (CP-004: o sexto portao) ----------------------------------
# O perfil de medicao mora em harness/perfis/: e da SUITE (derivado do
# podcast.yaml da audio-suite), e o Sprint 5 o calibra com as medicoes reais.
PERFIL_SONORO = HARNESS / "perfis" / "guardioes-narracao.yaml"


def _tem_audio_suite() -> bool:
    import shutil
    return shutil.which("audio-suite") is not None


def _exige_audio_suite() -> bool:
    """O ambiente PROMETEU a audio-suite (CP-007: o job do CI promete).

    ESTUDIO_EXIGIR_AUDIO_SUITE=1 e promessa local e explicita: quem a fez
    instalou a ferramenta (pinada por SHA) e quer que a ausencia dela
    REPROVE -- no CI, a medicao e contrato do job, e promessa quebrada e
    divida de infraestrutura. Na maquina local sem a variavel, o INDECISO
    nomeado segue de pe: "nao consegui medir" continua nao sendo "esta
    errado".
    """
    return os.environ.get("ESTUDIO_EXIGIR_AUDIO_SUITE") == "1"


def _publicar_sonorizacao(fid, estado, medidas=None, nota="", causa=""):
    """O estado do portao vira evidencia no relatorio.json do filme.

    Integrado aos tres estados existentes: verde/vermelho/indeciso sao a
    mesma moeda das outras etapas. O navegador regrava o relatorio dele por
    cima e PRESERVA esta chave -- o teste e que costura as duas escritas.
    CP-008: a causa do vermelho e publicada junto, porque "promessa
       quebrada" e "trilha reprovada" exigem correcoes diferentes.
    """
    import datetime
    import json
    rel = FILMES / fid / "relatorio.json"
    d = {}
    if rel.exists():
        try:
            d = json.loads(rel.read_text(encoding="utf-8"))
        except Exception:
            d = {}
    d["alvo"] = fid
    d["sonorizacao"] = {
        "estado": estado,
        "medidas": medidas or {},
        "nota": nota,
        "causa": causa,
        "quando": datetime.datetime.now(datetime.timezone.utc)
                  .isoformat(timespec="seconds"),
    }
    rel.parent.mkdir(parents=True, exist_ok=True)
    rel.write_text(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True)
                   + "\n", encoding="utf-8")


def portao_sonorizacao(fid):
    """A trilha que o filme DECLARA, medida pela audio-suite (CLI externa).

    So mede o filme que declara audio: true E tem audio/<id>.opus -- as duas
    coisas juntas, para nao fabricar falso positivo nem com artefato esquecido
    de uma dublagem abandonada, nem com declaracao sem entrega.

    Mapeamento da CP-004: 0 -> VERDE · 1 -> VERMELHO · 2, 3 ou ausencia do
    binario/perfil -> INDECISO. "Nao consegui medir" NAO e "esta errado":
    descritor nunca reprova, e a ausencia da ferramenta reprova menos ainda.
    """
    d = dados_do_filme(fid)
    opus = FILMES / fid / "audio" / f"{fid}.opus"
    declara = bool(d.get("audio"))

    if not declara and not opus.exists():
        return _v("sonorizacao", [], nota="filme mudo — nada a medir")
    if declara and not opus.exists():
        _publicar_sonorizacao(fid, "vermelho", nota="declara sem trilha",
                              causa="declaracao-divergente")
        v = _v("sonorizacao", [
            f"o filme declara audio, mas falta {opus.relative_to(RAIZ)} — "
            f"declare a dublagem rodando dublar, ou remova a declaracao"])
        v.causa = "declaracao-divergente"
        return v
    if not declara and opus.exists():
        _publicar_sonorizacao(fid, "vermelho", nota="trilha sem declaracao",
                              causa="declaracao-divergente")
        v = _v("sonorizacao", [
            f"existe {opus.relative_to(RAIZ)} sem o filme declarar audio: true — "
            f"a declaracao e o contrato da camada aditiva. Decida: declare, ou apague."])
        v.causa = "declaracao-divergente"
        return v

    if not _tem_audio_suite():
        if _exige_audio_suite():
            _publicar_sonorizacao(fid, "vermelho",
                                  nota="audio-suite exigida e ausente",
                                  causa="promessa-quebrada")
            v = _v("sonorizacao", [
                "ESTUDIO_EXIGIR_AUDIO_SUITE=1 promete a audio-suite, e ela nao "
                "esta no PATH — neste ambiente a ausencia da ferramenta e "
                "promessa quebrada (VERMELHO), nao INDECISO. Instale a "
                "audio-suite (isolada, pinada por SHA) ou desfaca a promessa."],
                nota="audio-suite exigida (ESTUDIO_EXIGIR_AUDIO_SUITE=1) e ausente")
            v.causa = "promessa-quebrada"
            return v
        _publicar_sonorizacao(fid, "indeciso", nota="audio-suite ausente")
        return _v("sonorizacao", [], indeciso=True,
                  nota="audio-suite ausente — NAO consigo medir (INDECISO, "
                       "nao aprovado). A audio-suite e CLI externa: "
                       "pip install -e danzeroum/audio-suite")
    if not PERFIL_SONORO.exists():
        _publicar_sonorizacao(fid, "indeciso", nota="sem perfil")
        return _v("sonorizacao", [], indeciso=True,
                  nota=f"falta o perfil {PERFIL_SONORO.relative_to(RAIZ)}")

    import json
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        # Decodificar nao e reamostrar: opus -> wav e mudanca de FORMATO,
        # mesma taxa (48 kHz), mesma duracao. O alvo da web e opus; a
        # audio-suite mede PCM. O sinal e o mesmo.
        wav = Path(tmp) / "medicao.wav"
        dec = subprocess.run(
            ["ffmpeg", "-y", "-nostdin", "-v", "error", "-i", str(opus),
             "-c:a", "pcm_s16le", str(wav)],
            capture_output=True, text=True, timeout=180)
        if dec.returncode != 0:
            _publicar_sonorizacao(fid, "indeciso", nota="decode falhou")
            return _v("sonorizacao", [f"nao consegui decodificar a trilha: "
                                      f"{dec.stderr[-160:]}"], indeciso=True)
        try:
            r = subprocess.run(
                ["audio-suite", "analyze", str(wav),
                 "--profile", str(PERFIL_SONORO), "--strict", "--format", "json"],
                capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            _publicar_sonorizacao(fid, "indeciso", nota="timeout da audio-suite")
            return _v("sonorizacao", [], indeciso=True,
                      nota="audio-suite nao respondeu (timeout) — INDECISO")

    medidas, reprovas = {}, []
    try:
        achados_json = json.loads(r.stdout)
        for f in achados_json.get("findings", []):
            medidas[f"{f.get('analyzer')}.{f.get('metric')}"] = f.get("value")
            if str(f.get("severity", "")).lower() in ("fail", "error"):
                reprovas.append(f"{f.get('analyzer')}: {f.get('message')}")
    except Exception:
        pass                                   # saida ilegivel cai no mapa abaixo

    if r.returncode == 0:
        # LUFS e true peak na frente: sao a ancora que um humano le, e a
        # CP-007 pediu as medidas reais publicadas por filme no portao.
        destaque = [k for k in ("loudness.integrated_loudness",
                                "true_peak.true_peak") if k in medidas]
        destaque += [k for k in sorted(medidas) if k not in destaque][:1]
        _publicar_sonorizacao(fid, "verde", medidas, "dentro das ancoras do perfil")
        return _v("sonorizacao", [],
                  nota="trilha dentro das ancoras do perfil "
                       + " · ".join(f"{k}={medidas[k]}" for k in destaque))
    if r.returncode == 1:
        _publicar_sonorizacao(fid, "vermelho", medidas, "audio-suite reprovou",
                              causa="trilha-reprovada")
        v = _v("sonorizacao", reprovas or ["audio-suite reprovou a trilha"],
               nota="saida 1 da audio-suite — FINDING")
        v.causa = "trilha-reprovada"
        return v
    # 2 (perfil invalido), 3 (entrada invalida), 64 (uso) e qualquer outro:
    # o portao nao conseguiu MEDIR. Nao e aprovado nem reprovado.
    _publicar_sonorizacao(fid, "indeciso", medidas,
                          f"audio-suite devolveu {r.returncode}")
    return _v("sonorizacao", [f"audio-suite devolveu {r.returncode} "
                              f"(2=perfil invalido, 3=entrada invalida): "
                              f"{(r.stderr or r.stdout)[-200:]}"], indeciso=True,
              nota="INDECISO — a ferramenta nao mediu")


PORTOES = {"recepcao": portao_recepcao, "roteiro": portao_roteiro,
           "storyboard": portao_storyboard, "animacao": portao_animacao,
           "acabamento": portao_acabamento, "sonorizacao": portao_sonorizacao}


def rodar(fid, ate=None):
    """Percorre as etapas em ordem e PARA na primeira que nao ficar verde."""
    saida = []
    for etapa in ETAPAS:
        v = PORTOES[etapa](fid)
        saida.append(v)
        if not v.ok:
            break
        if ate and etapa == ate:
            break
    return saida
