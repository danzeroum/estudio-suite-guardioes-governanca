/* A jornada de um dado pessoal — o roteiro, como DADO.
   Este arquivo é o que os analistas editam. Nenhuma linha de motor
   precisa mudar para ajustar tempo, pose, posição ou legenda.

   É JSON estrito dentro de um invólucro JS de uma linha: carrega por
   <script src> (logo funciona sob file://) e o mesmo arquivo é lido
   por tools/check-filme.py com json.loads. Mesmo truque de
   livro-lgpd/assets/guardioes.data.js.

   'em', 'ate' e 'dur' são RELATIVOS ao início do plano: inserir dois
   segundos numa cena não obriga a recalcular as seguintes.
   As legendas são as mesmas de estudio/roteiros/jornada-dado.md, e o
   validador recusa qualquer divergência entre os dois. */
window.ESTUDIO_FILMES=window.ESTUDIO_FILMES||{};window.ESTUDIO_FILMES["jornada-dado"]=
{
 "id": "jornada-dado",
 "titulo": "A jornada de um dado pessoal",
 "duracao": 124,
 "audio": true,
 "palco": {
  "w": 1280,
  "h": 720
 },
 "elenco": {
  "ana": {
   "rig": "raposa",
   "papel": "Titular"
  },
  "dpo": {
   "rig": "raposa",
   "papel": "Encarregado",
   "paleta": "alt"
  },
  "ctrl": {
   "rig": "coruja",
   "papel": "Controlador"
  },
  "op": {
   "rig": "tartaruga",
   "papel": "Operador"
  },
  "anpd": {
   "rig": "aguia",
   "papel": "ANPD"
  },
  "mem": {
   "rig": "elefante",
   "papel": "Registro e segurança"
  }
 },
 "props": {
  "dado": {
   "rig": "dado",
   "rotulo": "CPF",
   "camada": "efeitos"
  },
  "form": {
   "rig": "form"
  },
  "aviso": {
   "rig": "aviso"
  },
  "cartao": {
   "rig": "cartao"
  },
  "selo": {
   "rig": "selo"
  },
  "ficha": {
   "rig": "ficha"
  },
  "alarme": {
   "rig": "alarme"
  },
  "porta": {
   "rig": "porta",
   "camada": "cena"
  }
 },
 "planos": [
  {
   "id": "p01",
   "titulo": "Abertura",
   "dur": 6,
   "cenario": "vazio",
   "poster": 3.4,
   "arts": [],
   "entra": {
    "ctrl": {
     "x": 230,
     "y": 620,
     "escala": 1.05
    },
    "anpd": {
     "x": 440,
     "y": 620,
     "escala": 1.05
    },
    "op": {
     "x": 650,
     "y": 620,
     "escala": 1.05
    },
    "mem": {
     "x": 860,
     "y": 620,
     "escala": 1.05
    },
    "ana": {
     "x": 1070,
     "y": 620,
     "escala": 1.05
    },
    "dado": {
     "x": 640,
     "y": 300,
     "escala": 0.2,
     "op": 0
    }
   },
   "acoes": [
    {
     "em": 1.2,
     "dur": 2.2,
     "alvo": "dado",
     "para": {
      "escala": 1,
      "op": 1
     },
     "ease": "elastico"
    },
    {
     "em": 3.6,
     "dur": 2.0,
     "alvo": "ctrl",
     "para": {
      "op": 0.15
     }
    },
    {
     "em": 3.6,
     "dur": 2.0,
     "alvo": "anpd",
     "para": {
      "op": 0.15
     }
    },
    {
     "em": 3.6,
     "dur": 2.0,
     "alvo": "op",
     "para": {
      "op": 0.15
     }
    },
    {
     "em": 3.6,
     "dur": 2.0,
     "alvo": "mem",
     "para": {
      "op": 0.15
     }
    },
    {
     "em": 3.6,
     "dur": 2.0,
     "alvo": "ana",
     "para": {
      "op": 0.15
     }
    }
   ],
   "legendas": [
    {
     "em": 0.5,
     "ate": 5.5,
     "txt": "Todo dia, você deixa um rastro."
    }
   ]
  },
  {
   "id": "p02",
   "titulo": "O dado nasce",
   "dur": 9,
   "guardiao": "coruja",
   "cenario": "balcao",
   "poster": 5.2,
   "arts": [
    5
   ],
   "entra": {
    "ana": {
     "x": 330,
     "y": 620,
     "escala": 1.15,
     "pose": "neutro"
    },
    "ctrl": {
     "x": 940,
     "y": 620,
     "escala": 1.15,
     "pose": "neutro",
     "espelho": true
    },
    "form": {
     "x": 630,
     "y": 600,
     "escala": 1.15
    },
    "dado": {
     "x": 630,
     "y": 470,
     "escala": 0.25,
     "op": 0
    }
   },
   "acoes": [
    {
     "em": 0.6,
     "dur": 0.8,
     "alvo": "ana",
     "pose": "apontando"
    },
    {
     "em": 1.2,
     "dur": 0.6,
     "alvo": "form",
     "pose": "preenchido"
    },
    {
     "em": 2.0,
     "dur": 2.2,
     "alvo": "dado",
     "para": {
      "escala": 1,
      "op": 1
     },
     "ease": "elastico"
    },
    {
     "em": 2.4,
     "dur": 0.5,
     "alvo": "ana",
     "expressao": "surpreso"
    },
    {
     "em": 4.4,
     "dur": 0.8,
     "alvo": "ctrl",
     "pose": "apontando"
    },
    {
     "em": 4.6,
     "dur": 1.4,
     "alvo": "camera",
     "para": {
      "x": 700,
      "y": 470,
      "zoom": 1.18
     },
     "ease": "suave"
    },
    {
     "em": 6.2,
     "alvo": "dado",
     "evento": "citar",
     "dados": {
      "artigo": 5,
      "guardiao": "coruja"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 4.0,
     "txt": "Ana digita o CPF num formulário."
    },
    {
     "em": 4.3,
     "ate": 8.7,
     "txt": "A lei dá nome a isso: dado pessoal.\n(Art. 5º)",
     "ref": 5
    }
   ]
  },
  {
   "id": "p03",
   "titulo": "O que te contam",
   "dur": 9,
   "guardiao": "coruja",
   "cenario": "balcao",
   "poster": 5.6,
   "arts": [
    9
   ],
   "entra": {
    "ana": {
     "x": 300,
     "y": 620,
     "escala": 1.1
    },
    "ctrl": {
     "x": 960,
     "y": 620,
     "escala": 1.1,
     "pose": "apontando",
     "espelho": true
    },
    "aviso": {
     "x": 640,
     "y": 560,
     "escala": 1.1,
     "pose": "neutro"
    },
    "dado": {
     "x": 640,
     "y": 392,
     "escala": 0.7
    }
   },
   "acoes": [
    {
     "em": 1.0,
     "dur": 1.6,
     "alvo": "aviso",
     "pose": "aberto",
     "ease": "saida"
    },
    {
     "em": 3.2,
     "dur": 0.6,
     "alvo": "ana",
     "expressao": "feliz"
    },
    {
     "em": 5.0,
     "alvo": "aviso",
     "evento": "destacar",
     "dados": {
      "artigo": 9,
      "guardiao": "coruja"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 4.3,
     "txt": "Ana tem direito de saber o que farão"
    },
    {
     "em": 4.5,
     "ate": 8.7,
     "txt": "com o dado dela — antes, não depois.\n(Art. 9º)",
     "ref": 9
    }
   ]
  },
  {
   "id": "p04",
   "titulo": "O consentimento",
   "dur": 11,
   "guardiao": "raposa",
   "cenario": "balcao",
   "poster": 4.0,
   "arts": [
    8
   ],
   "entra": {
    "ana": {
     "x": 300,
     "y": 620,
     "escala": 1.1
    },
    "dpo": {
     "x": 940,
     "y": 620,
     "escala": 1.1,
     "pose": "entregando",
     "espelho": true
    },
    "cartao": {
     "x": 630,
     "y": 520,
     "escala": 1.2
    },
    "dado": {
     "x": 630,
     "y": 372,
     "escala": 0.7
    }
   },
   "acoes": [
    {
     "em": 0.8,
     "dur": 1.2,
     "alvo": "cartao",
     "para": {
      "y": 500
     },
     "ease": "saida"
    },
    {
     "em": 3.4,
     "dur": 0.6,
     "alvo": "cartao",
     "pose": "aceito"
    },
    {
     "em": 3.6,
     "dur": 0.6,
     "alvo": "ana",
     "expressao": "feliz"
    },
    {
     "em": 8.4,
     "dur": 1.0,
     "alvo": "cartao",
     "pose": "revogado"
    },
    {
     "em": 8.6,
     "alvo": "cartao",
     "evento": "citar",
     "dados": {
      "artigo": 8,
      "guardiao": "raposa"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 4.5,
     "txt": "A Raposa pede permissão em destaque,"
    },
    {
     "em": 4.7,
     "ate": 8.0,
     "txt": "separada de qualquer outro texto."
    },
    {
     "em": 8.2,
     "ate": 10.8,
     "txt": "E ela pode ser revogada. (Art. 8º)",
     "ref": 8
    }
   ]
  },
  {
   "id": "p05",
   "titulo": "A rota legal",
   "dur": 11,
   "guardiao": "aguia",
   "cenario": "painel",
   "poster": 8.6,
   "arts": [
    7
   ],
   "entra": {
    "anpd": {
     "x": 1030,
     "y": 620,
     "escala": 1.1,
     "espelho": true
    },
    "dado": {
     "x": 250,
     "y": 460,
     "escala": 0.8
    },
    "selo": {
     "x": 600,
     "y": 400,
     "escala": 0.9,
     "pose": "neutro"
    }
   },
   "acoes": [
    {
     "em": 1.0,
     "dur": 2.4,
     "alvo": "dado",
     "para": {
      "x": 470
     },
     "ease": "suave"
    },
    {
     "em": 4.0,
     "dur": 0.8,
     "alvo": "anpd",
     "pose": "apontando"
    },
    {
     "em": 7.6,
     "dur": 0.9,
     "alvo": "selo",
     "pose": "carimbado",
     "ease": "elastico"
    },
    {
     "em": 8.2,
     "alvo": "selo",
     "evento": "citar",
     "dados": {
      "artigo": 7,
      "guardiao": "aguia"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 4.0,
     "txt": "Consentimento é só uma das dez rotas"
    },
    {
     "em": 4.2,
     "ate": 7.8,
     "txt": "que a lei permite para tratar dados."
    },
    {
     "em": 8.0,
     "ate": 10.8,
     "txt": "A Águia carimba a escolhida. (Art. 7º)",
     "ref": 7
    }
   ]
  },
  {
   "id": "p06",
   "titulo": "Os dez princípios",
   "dur": 13,
   "guardiao": "tartaruga",
   "cenario": "principios",
   "poster": 9.0,
   "arts": [
    6
   ],
   "entra": {
    "op": {
     "x": 640,
     "y": 620,
     "escala": 1.25
    },
    "dado": {
     "x": 960,
     "y": 440,
     "escala": 1
    }
   },
   "acoes": [
    {
     "em": 1.6,
     "dur": 1.4,
     "alvo": "op",
     "pose": "protegendo",
     "ease": "saida"
    },
    {
     "em": 4.0,
     "dur": 2.6,
     "alvo": "camera",
     "para": {
      "x": 600,
      "y": 430,
      "zoom": 1.12
     },
     "ease": "suave"
    },
    {
     "em": 5.0,
     "dur": 2.0,
     "alvo": "dado",
     "para": {
      "x": 880
     },
     "ease": "suave"
    },
    {
     "em": 9.0,
     "alvo": "op",
     "evento": "destacar",
     "dados": {
      "artigo": 6,
      "guardiao": "tartaruga"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 4.2,
     "txt": "Escolher a rota não basta."
    },
    {
     "em": 4.4,
     "ate": 8.6,
     "txt": "Dez princípios valem para todo tratamento"
    },
    {
     "em": 8.8,
     "ate": 12.8,
     "txt": "— da finalidade à prestação de contas.\n(Art. 6º)",
     "ref": 6
    }
   ]
  },
  {
   "id": "p07",
   "titulo": "Quem manda, quem executa",
   "dur": 10,
   "guardiao": "raposa",
   "cenario": "estacoes",
   "poster": 6.4,
   "arts": [
    39
   ],
   "entra": {
    "ctrl": {
     "x": 300,
     "y": 620,
     "escala": 1.05
    },
    "op": {
     "x": 990,
     "y": 620,
     "escala": 1.05,
     "espelho": true
    },
    "dado": {
     "x": 640,
     "y": 430,
     "escala": 0.8
    }
   },
   "acoes": [
    {
     "em": 1.0,
     "dur": 1.0,
     "alvo": "ctrl",
     "pose": "entregando"
    },
    {
     "em": 2.6,
     "dur": 2.4,
     "alvo": "dado",
     "para": {
      "x": 880
     },
     "ease": "suave"
    },
    {
     "em": 5.6,
     "dur": 0.7,
     "alvo": "op",
     "expressao": "preocupado"
    },
    {
     "em": 6.0,
     "dur": 0.9,
     "alvo": "op",
     "pose": "protegendo"
    },
    {
     "em": 7.2,
     "alvo": "op",
     "evento": "citar",
     "dados": {
      "artigo": 39,
      "guardiao": "raposa"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 4.5,
     "txt": "O operador só faz o que foi instruído."
    },
    {
     "em": 4.7,
     "ate": 9.8,
     "txt": "Sair da instrução o torna responsável\njunto. (Art. 39)",
     "ref": 39
    }
   ]
  },
  {
   "id": "p08",
   "titulo": "O registro",
   "dur": 11,
   "guardiao": "elefante",
   "cenario": "arquivo",
   "poster": 6.8,
   "arts": [
    37,
    38
   ],
   "entra": {
    "mem": {
     "x": 400,
     "y": 620,
     "escala": 1.05
    },
    "ficha": {
     "x": 790,
     "y": 540,
     "escala": 1.05
    },
    "dado": {
     "x": 1010,
     "y": 440,
     "escala": 0.75
    }
   },
   "acoes": [
    {
     "em": 1.2,
     "dur": 1.0,
     "alvo": "mem",
     "pose": "entregando"
    },
    {
     "em": 3.2,
     "dur": 1.2,
     "alvo": "ficha",
     "pose": "arquivada",
     "ease": "saida"
    },
    {
     "em": 5.6,
     "dur": 1.0,
     "alvo": "mem",
     "expressao": "feliz"
    },
    {
     "em": 7.0,
     "alvo": "ficha",
     "evento": "citar",
     "dados": {
      "artigo": 37,
      "guardiao": "elefante"
     }
    },
    {
     "em": 8.4,
     "alvo": "ficha",
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
     "ate": 4.4,
     "txt": "O Elefante registra cada operação."
    },
    {
     "em": 4.6,
     "ate": 8.4,
     "txt": "Sem registro, não há como provar nada."
    },
    {
     "em": 8.6,
     "ate": 10.8,
     "txt": "(Arts. 37 e 38)",
     "ref": 37
    }
   ]
  },
  {
   "id": "p09",
   "titulo": "A fronteira",
   "dur": 11,
   "guardiao": "aguia",
   "cenario": "fronteira",
   "poster": 8.8,
   "arts": [
    33
   ],
   "entra": {
    "anpd": {
     "x": 420,
     "y": 620,
     "escala": 1.1
    },
    "dado": {
     "x": 300,
     "y": 430,
     "escala": 0.9
    },
    "selo": {
     "x": 840,
     "y": 360,
     "escala": 0.9,
     "pose": "neutro"
    }
   },
   "acoes": [
    {
     "em": 0.8,
     "dur": 2.6,
     "alvo": "dado",
     "para": {
      "x": 560
     },
     "ease": "suave"
    },
    {
     "em": 2.4,
     "dur": 0.9,
     "alvo": "anpd",
     "pose": "protegendo"
    },
    {
     "em": 5.4,
     "dur": 0.8,
     "alvo": "anpd",
     "pose": "apontando"
    },
    {
     "em": 6.2,
     "dur": 2.0,
     "alvo": "dado",
     "para": {
      "x": 860
     },
     "ease": "suave"
    },
    {
     "em": 8.2,
     "dur": 0.9,
     "alvo": "selo",
     "pose": "carimbado",
     "ease": "elastico"
    },
    {
     "em": 8.6,
     "alvo": "selo",
     "evento": "citar",
     "dados": {
      "artigo": 33,
      "guardiao": "aguia"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 4.4,
     "txt": "O dado quer atravessar a fronteira."
    },
    {
     "em": 4.6,
     "ate": 8.2,
     "txt": "Nove hipóteses permitem isso —"
    },
    {
     "em": 8.4,
     "ate": 11.0,
     "txt": "e alguém precisa conferir. (Art. 33)",
     "ref": 33
    }
   ]
  },
  {
   "id": "p10",
   "titulo": "A segurança",
   "dur": 12,
   "guardiao": "elefante",
   "cenario": "cofre",
   "poster": 3.0,
   "arts": [
    46
   ],
   "entra": {
    "mem": {
     "x": 330,
     "y": 620,
     "escala": 1.15
    },
    "dado": {
     "x": 700,
     "y": 440,
     "escala": 0.9
    },
    "alarme": {
     "x": 1120,
     "y": 300,
     "escala": 0.85
    },
    "porta": {
     "x": 980,
     "y": 536,
     "escala": 1.95,
     "pose": "fechada"
    }
   },
   "acoes": [
    {
     "em": 0.6,
     "dur": 0.6,
     "alvo": "mem",
     "expressao": "preocupado"
    },
    {
     "em": 0.8,
     "dur": 0.8,
     "alvo": "porta",
     "pose": "entreaberta",
     "ease": "saida"
    },
    {
     "em": 1.4,
     "dur": 1.6,
     "alvo": "dado",
     "para": {
      "x": 880,
      "y": 470
     },
     "ease": "entrada"
    },
    {
     "em": 1.6,
     "dur": 0.8,
     "alvo": "dado",
     "pose": "retraido"
    },
    {
     "em": 2.8,
     "dur": 0.9,
     "alvo": "mem",
     "pose": "protegendo",
     "ease": "saida"
    },
    {
     "em": 3.8,
     "dur": 1.4,
     "alvo": "dado",
     "para": {
      "x": 700,
      "y": 440
     },
     "ease": "saida"
    },
    {
     "em": 4.4,
     "dur": 0.7,
     "alvo": "porta",
     "pose": "fechada",
     "ease": "saida"
    },
    {
     "em": 5.0,
     "dur": 0.8,
     "alvo": "dado",
     "pose": "neutro"
    },
    {
     "em": 7.0,
     "dur": 1.0,
     "alvo": "mem",
     "expressao": "neutro"
    },
    {
     "em": 7.8,
     "dur": 1.6,
     "alvo": "porta",
     "pose": "projeto",
     "ease": "suave"
    },
    {
     "em": 8.0,
     "alvo": "mem",
     "evento": "citar",
     "dados": {
      "artigo": 46,
      "guardiao": "elefante"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 3.6,
     "txt": "Uma porta fica destrancada."
    },
    {
     "em": 3.8,
     "ate": 7.6,
     "txt": "Segurança não é remendo do fim:"
    },
    {
     "em": 7.8,
     "ate": 11.8,
     "txt": "ela nasce com o produto. (Art. 46)",
     "ref": 46
    }
   ]
  },
  {
   "id": "p11",
   "titulo": "O alarme",
   "dur": 10,
   "guardiao": "aguia",
   "cenario": "cofre",
   "poster": 6.0,
   "arts": [
    48
   ],
   "entra": {
    "dpo": {
     "x": 300,
     "y": 620,
     "escala": 1.1,
     "expressao": "preocupado"
    },
    "anpd": {
     "x": 1010,
     "y": 620,
     "escala": 1.1,
     "espelho": true
    },
    "alarme": {
     "x": 640,
     "y": 300,
     "escala": 1
    },
    "dado": {
     "x": 640,
     "y": 470,
     "escala": 0.7
    },
    "porta": {
     "x": 980,
     "y": 536,
     "escala": 1.95,
     "pose": "fechada"
    }
   },
   "acoes": [
    {
     "em": 0.6,
     "dur": 0.8,
     "alvo": "alarme",
     "pose": "tocando",
     "ease": "saida"
    },
    {
     "em": 2.0,
     "dur": 1.0,
     "alvo": "dpo",
     "pose": "entregando"
    },
    {
     "em": 4.4,
     "dur": 0.9,
     "alvo": "anpd",
     "pose": "apontando"
    },
    {
     "em": 6.0,
     "alvo": "alarme",
     "evento": "citar",
     "dados": {
      "artigo": 48,
      "guardiao": "aguia"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 4.2,
     "txt": "Incidente relevante não se esconde."
    },
    {
     "em": 4.4,
     "ate": 9.8,
     "txt": "A ANPD e o titular precisam ser\navisados. (Art. 48)",
     "ref": 48
    }
   ]
  },
  {
   "id": "p12",
   "titulo": "O titular volta",
   "dur": 11,
   "guardiao": "aguia",
   "cenario": "balcao",
   "poster": 9.4,
   "arts": [
    18
   ],
   "entra": {
    "ana": {
     "x": 160,
     "y": 620,
     "escala": 0.82
    },
    "dpo": {
     "x": 370,
     "y": 620,
     "escala": 0.82
    },
    "ctrl": {
     "x": 575,
     "y": 620,
     "escala": 0.82
    },
    "op": {
     "x": 780,
     "y": 620,
     "escala": 0.82
    },
    "mem": {
     "x": 985,
     "y": 620,
     "escala": 0.82
    },
    "anpd": {
     "x": 1120,
     "y": 620,
     "escala": 0.82
    },
    "dado": {
     "x": 640,
     "y": 420,
     "escala": 0.9
    }
   },
   "acoes": [
    {
     "em": 0.8,
     "dur": 0.8,
     "alvo": "ana",
     "pose": "apontando"
    },
    {
     "em": 2.4,
     "dur": 0.8,
     "alvo": "dpo",
     "pose": "entregando"
    },
    {
     "em": 3.4,
     "dur": 0.8,
     "alvo": "ctrl",
     "pose": "apontando"
    },
    {
     "em": 4.4,
     "dur": 0.8,
     "alvo": "op",
     "pose": "entregando"
    },
    {
     "em": 5.4,
     "dur": 0.8,
     "alvo": "mem",
     "pose": "entregando"
    },
    {
     "em": 7.0,
     "dur": 2.4,
     "alvo": "dado",
     "para": {
      "escala": 0.2,
      "op": 0
     },
     "ease": "entrada"
    },
    {
     "em": 7.2,
     "dur": 1.0,
     "alvo": "ana",
     "expressao": "feliz"
    },
    {
     "em": 9.0,
     "alvo": "ana",
     "evento": "marco",
     "dados": {
      "artigo": 18,
      "guardiao": "aguia"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 4.2,
     "txt": "Ana pede seus dados de volta."
    },
    {
     "em": 4.4,
     "ate": 8.0,
     "txt": "São nove direitos, e o relógio corre."
    },
    {
     "em": 8.2,
     "ate": 10.8,
     "txt": "O dado sempre teve dono. (Art. 18)",
     "ref": 18
    }
   ]
  }
 ],
 "cobertura": "completa"
}
;
