/* O relatório de impacto — o TERCEIRO filme. Escrito só como dado, sem arte
   nova e sem trilha: a legenda é o filme (pedido.md). O roteiro em prosa
   está em filmes/relatorio-impacto/roteiro.md.

   ATENÇÃO: as citações (Art. 38 → elefante, Art. 10 → tartaruga) estão
   PENDENTES de conferência contra o lei.lock -- ver o roteiro. */
window.ESTUDIO_FILMES=window.ESTUDIO_FILMES||{};window.ESTUDIO_FILMES["relatorio-impacto"]=
{
 "id": "relatorio-impacto",
 "titulo": "O relatório de impacto",
 "duracao": 35,
 "palco": {
  "w": 1280,
  "h": 720
 },
 "elenco": {
  "ctrl": {
   "rig": "coruja",
   "papel": "Controlador"
  },
  "mem": {
   "rig": "elefante",
   "papel": "Registro"
  },
  "op": {
   "rig": "tartaruga",
   "papel": "Operador"
  }
 },
 "props": {
  "dado": {
   "rig": "dado",
   "camada": "efeitos"
  },
  "alarme": {
   "rig": "alarme"
  },
  "form": {
   "rig": "form"
  },
  "selo": {
   "rig": "selo"
  }
 },
 "planos": [
  {
   "id": "p01",
   "titulo": "Todo mundo fala em RIPD",
   "dur": 5,
   "cenario": "painel",
   "poster": 3.0,
   "arts": [],
   "entra": {
    "ctrl": {
     "x": 930,
     "y": 620,
     "escala": 1.1,
     "espelho": true,
     "expressao": "preocupado"
    },
    "dado": {
     "x": 520,
     "y": 430,
     "escala": 0.2,
     "op": 0
    }
   },
   "acoes": [
    {
     "em": 0.6,
     "dur": 1.8,
     "alvo": "dado",
     "para": {
      "escala": 0.9,
      "op": 1
     },
     "ease": "elastico"
    },
    {
     "em": 2.6,
     "dur": 1.8,
     "alvo": "camera",
     "para": {
      "x": 640,
      "y": 400,
      "zoom": 1.08
     },
     "ease": "suave"
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 2.3,
     "txt": "Todo mundo fala em RIPD."
    },
    {
     "em": 2.5,
     "ate": 4.8,
     "txt": "Pouca gente pergunta o que é."
    }
   ]
  },
  {
   "id": "p02",
   "titulo": "Uma pergunta, não papelada",
   "dur": 8,
   "cenario": "principios",
   "poster": 6.0,
   "arts": [],
   "entra": {
    "ctrl": {
     "x": 300,
     "y": 620,
     "escala": 1.1
    },
    "dado": {
     "x": 760,
     "y": 450,
     "escala": 0.85
    },
    "alarme": {
     "x": 760,
     "y": 250,
     "escala": 0.9
    }
   },
   "acoes": [
    {
     "em": 2.8,
     "dur": 0.8,
     "alvo": "alarme",
     "pose": "tocando",
     "ease": "saida"
    },
    {
     "em": 3.2,
     "dur": 0.6,
     "alvo": "dado",
     "pose": "retraido"
    },
    {
     "em": 3.4,
     "dur": 0.8,
     "alvo": "ctrl",
     "pose": "apontando"
    },
    {
     "em": 5.0,
     "dur": 2.2,
     "alvo": "camera",
     "para": {
      "x": 680,
      "y": 420,
      "zoom": 1.12
     },
     "ease": "suave"
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 2.8,
     "txt": "Não é papelada. É uma pergunta,"
    },
    {
     "em": 3.0,
     "ate": 5.0,
     "txt": "feita antes e por escrito:"
    },
    {
     "em": 5.2,
     "ate": 7.8,
     "txt": "esse tratamento vale o risco que cria?"
    }
   ]
  },
  {
   "id": "p03",
   "titulo": "A ANPD pode exigir",
   "dur": 8,
   "guardiao": "elefante",
   "cenario": "arquivo",
   "poster": 5.5,
   "arts": [
    38
   ],
   "entra": {
    "mem": {
     "x": 380,
     "y": 620,
     "escala": 1.1
    },
    "form": {
     "x": 800,
     "y": 560,
     "escala": 1.15
    },
    "dado": {
     "x": 800,
     "y": 400,
     "escala": 0.7
    }
   },
   "acoes": [
    {
     "em": 1.0,
     "dur": 0.8,
     "alvo": "mem",
     "pose": "entregando"
    },
    {
     "em": 2.2,
     "dur": 0.8,
     "alvo": "form",
     "pose": "preenchido"
    },
    {
     "em": 6.6,
     "alvo": "mem",
     "evento": "citar",
     "dados": {
      "artigo": 38,
      "guardiao": "elefante"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 3.6,
     "txt": "A ANPD pode determinar que o controlador"
    },
    {
     "em": 3.8,
     "ate": 6.4,
     "txt": "faça o relatório de impacto."
    },
    {
     "em": 6.6,
     "ate": 7.8,
     "txt": "(Art. 38)",
     "ref": 38
    }
   ]
  },
  {
   "id": "p04",
   "titulo": "O que ele responde",
   "dur": 8,
   "guardiao": "elefante",
   "cenario": "arquivo",
   "poster": 6.0,
   "arts": [
    38
   ],
   "entra": {
    "mem": {
     "x": 330,
     "y": 620,
     "escala": 1.1,
     "pose": "apontando"
    },
    "form": {
     "x": 760,
     "y": 560,
     "escala": 1.2,
     "pose": "preenchido"
    },
    "selo": {
     "x": 760,
     "y": 360,
     "escala": 0.9,
     "pose": "neutro"
    },
    "dado": {
     "x": 1060,
     "y": 430,
     "escala": 0.7,
     "pose": "retraido"
    }
   },
   "acoes": [
    {
     "em": 3.6,
     "dur": 0.9,
     "alvo": "selo",
     "pose": "carimbado",
     "ease": "elastico"
    },
    {
     "em": 5.0,
     "dur": 0.8,
     "alvo": "dado",
     "pose": "neutro"
    },
    {
     "em": 6.7,
     "alvo": "selo",
     "evento": "citar",
     "dados": {
      "artigo": 38,
      "guardiao": "elefante"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 3.5,
     "txt": "Descreve os dados, como são coletados"
    },
    {
     "em": 3.7,
     "ate": 6.6,
     "txt": "e protegidos, e o que reduz o risco."
    },
    {
     "em": 6.7,
     "ate": 7.9,
     "txt": "(Art. 38)",
     "ref": 38
    }
   ]
  },
  {
   "id": "p05",
   "titulo": "No legítimo interesse",
   "dur": 6,
   "guardiao": "tartaruga",
   "cenario": "principios",
   "poster": 4.0,
   "arts": [
    10
   ],
   "entra": {
    "op": {
     "x": 460,
     "y": 620,
     "escala": 1.15
    },
    "dado": {
     "x": 820,
     "y": 440,
     "escala": 0.85
    }
   },
   "acoes": [
    {
     "em": 0.6,
     "dur": 1.0,
     "alvo": "op",
     "pose": "protegendo",
     "ease": "saida"
    },
    {
     "em": 1.8,
     "dur": 3.0,
     "alvo": "camera",
     "para": {
      "x": 640,
      "y": 360,
      "zoom": 0.88
     },
     "ease": "suave"
    },
    {
     "em": 3.0,
     "alvo": "op",
     "evento": "marco",
     "dados": {
      "artigo": 10,
      "guardiao": "tartaruga"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 2.8,
     "txt": "Se a base é o legítimo interesse,"
    },
    {
     "em": 3.0,
     "ate": 5.8,
     "txt": "a ANPD pode pedir o relatório. (Art. 10)",
     "ref": 10
    }
   ]
  }
 ]
}
;
