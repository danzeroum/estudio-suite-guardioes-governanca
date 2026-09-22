/* O teste do legítimo interesse — o SEGUNDO filme, e a prova do template.
   Escrito só como dado: o objetivo desta fase era descobrir se um filme
   novo nasce sem tocar no motor. O relatório está em
   estudio/roteiros/legitimo-interesse.md.

   Exercita de propósito o que o filme 01 nunca usou: a pose 'andando',
   a ação 'estado', três instâncias do mesmo rig, o evento 'marco' e
   zoom menor que 1. */
window.ESTUDIO_FILMES=window.ESTUDIO_FILMES||{};window.ESTUDIO_FILMES["legitimo-interesse"]=
{
 "id": "legitimo-interesse",
 "titulo": "O teste do legítimo interesse",
 "duracao": 42,
 "palco": {
  "w": 1280,
  "h": 720
 },
 "elenco": {
  "ana": {
   "rig": "raposa",
   "papel": "Titular"
  },
  "ctrl": {
   "rig": "coruja",
   "papel": "Controlador"
  },
  "op": {
   "rig": "tartaruga",
   "papel": "Operador"
  },
  "mem": {
   "rig": "elefante",
   "papel": "Registro"
  }
 },
 "props": {
  "dado": {
   "rig": "dado",
   "camada": "efeitos"
  },
  "dado2": {
   "rig": "dado",
   "camada": "efeitos"
  },
  "dado3": {
   "rig": "dado",
   "camada": "efeitos"
  },
  "aviso": {
   "rig": "aviso"
  },
  "ficha": {
   "rig": "ficha"
  }
 },
 "planos": [
  {
   "id": "p01",
   "titulo": "A pergunta",
   "dur": 7,
   "cenario": "balcao",
   "poster": 4.5,
   "arts": [],
   "entra": {
    "ana": {
     "x": 340,
     "y": 620,
     "escala": 1.1,
     "expressao": "preocupado"
    },
    "ctrl": {
     "x": 930,
     "y": 620,
     "escala": 1.1,
     "espelho": true,
     "pose": "apontando"
    },
    "dado": {
     "x": 640,
     "y": 430,
     "escala": 0.85
    }
   },
   "acoes": [
    {
     "em": 2.0,
     "dur": 0.8,
     "alvo": "ctrl",
     "pose": "entregando"
    },
    {
     "em": 4.2,
     "dur": 1.4,
     "alvo": "camera",
     "para": {
      "x": 700,
      "y": 430,
      "zoom": 1.1
     },
     "ease": "suave"
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 3.4,
     "txt": "Nem todo tratamento pede consentimento."
    },
    {
     "em": 3.6,
     "ate": 6.8,
     "txt": "Às vezes basta o legítimo interesse."
    }
   ]
  },
  {
   "id": "p02",
   "titulo": "Situações concretas",
   "dur": 10,
   "guardiao": "tartaruga",
   "cenario": "principios",
   "poster": 7.0,
   "arts": [
    10
   ],
   "entra": {
    "op": {
     "x": 120,
     "y": 620,
     "escala": 1.2,
     "pose": "andando"
    },
    "dado": {
     "x": 960,
     "y": 440,
     "escala": 0.9
    }
   },
   "acoes": [
    {
     "em": 0.4,
     "dur": 3.4,
     "alvo": "op",
     "para": {
      "x": 640
     },
     "ease": "suave"
    },
    {
     "em": 3.8,
     "dur": 1.0,
     "alvo": "op",
     "pose": "protegendo",
     "ease": "saida"
    },
    {
     "em": 5.6,
     "dur": 2.0,
     "alvo": "camera",
     "para": {
      "x": 700,
      "y": 460,
      "zoom": 1.12
     },
     "ease": "suave"
    },
    {
     "em": 7.8,
     "alvo": "op",
     "evento": "citar",
     "dados": {
      "artigo": 10,
      "guardiao": "tartaruga"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 4.2,
     "txt": "Mas legítimo interesse não é cheque"
    },
    {
     "em": 4.4,
     "ate": 7.6,
     "txt": "em branco: precisa de situação concreta."
    },
    {
     "em": 7.8,
     "ate": 9.8,
     "txt": "(Art. 10)",
     "ref": 10
    }
   ]
  },
  {
   "id": "p03",
   "titulo": "Só o estritamente necessário",
   "dur": 10,
   "guardiao": "tartaruga",
   "cenario": "principios",
   "poster": 6.5,
   "arts": [
    10
   ],
   "entra": {
    "op": {
     "x": 330,
     "y": 620,
     "escala": 1.2,
     "pose": "apontando"
    },
    "dado": {
     "x": 760,
     "y": 430,
     "escala": 0.8
    },
    "dado2": {
     "x": 910,
     "y": 430,
     "escala": 0.8
    },
    "dado3": {
     "x": 1060,
     "y": 430,
     "escala": 0.8
    }
   },
   "acoes": [
    {
     "em": 3.6,
     "alvo": "dado2",
     "estado": "apagado"
    },
    {
     "em": 4.6,
     "alvo": "dado3",
     "estado": "apagado"
    },
    {
     "em": 5.4,
     "dur": 1.2,
     "alvo": "dado",
     "para": {
      "escala": 1.0
     },
     "ease": "elastico"
    },
    {
     "em": 7.6,
     "alvo": "op",
     "evento": "citar",
     "dados": {
      "artigo": 10,
      "guardiao": "tartaruga"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 4.0,
     "txt": "E só os dados estritamente necessários"
    },
    {
     "em": 4.2,
     "ate": 7.4,
     "txt": "para aquela finalidade — nem um a mais."
    },
    {
     "em": 7.6,
     "ate": 9.8,
     "txt": "(Art. 10)",
     "ref": 10
    }
   ]
  },
  {
   "id": "p04",
   "titulo": "E o titular precisa saber",
   "dur": 8,
   "guardiao": "coruja",
   "cenario": "balcao",
   "poster": 5.0,
   "arts": [
    9
   ],
   "entra": {
    "ana": {
     "x": 340,
     "y": 620,
     "escala": 1.1,
     "expressao": "preocupado"
    },
    "ctrl": {
     "x": 930,
     "y": 620,
     "escala": 1.1,
     "espelho": true,
     "pose": "apontando"
    },
    "aviso": {
     "x": 640,
     "y": 560,
     "escala": 1.05
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
     "em": 3.4,
     "dur": 0.8,
     "alvo": "ana",
     "expressao": "feliz"
    },
    {
     "em": 5.0,
     "alvo": "aviso",
     "evento": "citar",
     "dados": {
      "artigo": 9,
      "guardiao": "coruja"
     }
    }
   ],
   "legendas": [
    {
     "em": 0.3,
     "ate": 4.0,
     "txt": "O titular tem de saber que foi essa"
    },
    {
     "em": 4.2,
     "ate": 7.8,
     "txt": "a base escolhida, e por quê. (Art. 9º)",
     "ref": 9
    }
   ]
  },
  {
   "id": "p05",
   "titulo": "E a ANPD pode pedir o relatório",
   "dur": 7,
   "guardiao": "elefante",
   "cenario": "arquivo",
   "poster": 4.0,
   "arts": [
    38
   ],
   "entra": {
    "mem": {
     "x": 420,
     "y": 620,
     "escala": 1.05,
     "pose": "entregando"
    },
    "ficha": {
     "x": 760,
     "y": 520,
     "escala": 1.0
    },
    "dado": {
     "x": 980,
     "y": 430,
     "escala": 0.75
    }
   },
   "acoes": [
    {
     "em": 0.2,
     "dur": 1.0,
     "alvo": "camera",
     "para": {
      "zoom": 1.14
     },
     "ease": "saida"
    },
    {
     "em": 1.6,
     "dur": 3.4,
     "alvo": "camera",
     "para": {
      "x": 640,
      "y": 360,
      "zoom": 0.86
     },
     "ease": "suave"
    },
    {
     "em": 3.8,
     "alvo": "mem",
     "evento": "marco",
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
     "txt": "E a ANPD pode pedir o relatório"
    },
    {
     "em": 3.8,
     "ate": 6.8,
     "txt": "de impacto a qualquer momento. (Art. 38)",
     "ref": 38
    }
   ]
  }
 ]
}
;
