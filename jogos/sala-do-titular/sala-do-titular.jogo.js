/* Sala do Titular — os nove direitos do Art. 18.
   O campo 'texto' de cada direito é o TEXTO LITERAL da lei, copiado de
   docs/assets/data/lgpd-arts.json; tools/check-filme.py compara os dois
   byte a byte e reprova qualquer divergência. Fica embutido aqui, e não
   é buscado por fetch, pela mesma razão de sempre: sob file:// o fetch
   morre e o <script src> vizinho não. Mesmo motivo de
   livro-lgpd/assets/guardioes.data.js.

   'rotulo' e 'pedido' são a camada autoral: curta, num arquivo só, e
   validada contra os incisos acima. */
window.ESTUDIO_JOGOS=window.ESTUDIO_JOGOS||{};window.ESTUDIO_JOGOS["sala-do-titular"]=
{
 "id": "sala-do-titular",
 "titulo": "Sala do Titular",
 "subtitulo": "Os nove direitos do Art. 18, do lado de quem responde",
 "artigo": 18,
 "guardiao": "aguia",
 "prazo": 12,
 "semente": 20260922,
 "direitos": [
  {
   "inciso": "I",
   "rotulo": "Confirmação de que existe tratamento",
   "texto": "confirmação da existência de tratamento"
  },
  {
   "inciso": "II",
   "rotulo": "Acesso aos dados",
   "texto": "acesso aos dados"
  },
  {
   "inciso": "III",
   "rotulo": "Correção de dados errados",
   "texto": "correção de dados incompletos, inexatos ou desatualizados"
  },
  {
   "inciso": "IV",
   "rotulo": "Anonimização, bloqueio ou eliminação de dados desnecessários",
   "texto": "anonimização, bloqueio ou eliminação de dados desnecessários, excessivos ou tratados em desconformidade com o disposto nesta Lei"
  },
  {
   "inciso": "V",
   "rotulo": "Portabilidade para outro fornecedor",
   "texto": "portabilidade dos dados a outro fornecedor de serviço ou produto, mediante requisição expressa, de acordo com a regulamentação da autoridade nacional, observados os segredos comercial e industrial"
  },
  {
   "inciso": "VI",
   "rotulo": "Eliminação dos dados consentidos",
   "texto": "eliminação dos dados pessoais tratados com o consentimento do titular, exceto nas hipóteses previstas no art. 16 desta Lei"
  },
  {
   "inciso": "VII",
   "rotulo": "Informação sobre compartilhamento",
   "texto": "informação das entidades públicas e privadas com as quais o controlador realizou uso compartilhado de dados"
  },
  {
   "inciso": "VIII",
   "rotulo": "Informação sobre não consentir",
   "texto": "informação sobre a possibilidade de não fornecer consentimento e sobre as consequências da negativa"
  },
  {
   "inciso": "IX",
   "rotulo": "Revogação do consentimento",
   "texto": "revogação do consentimento, nos termos do § 5º do art. 8º desta Lei"
  }
 ],
 "situacoes": [
  {
   "inciso": "I",
   "pedido": "Vocês têm algum dado meu? Só quero saber se têm."
  },
  {
   "inciso": "II",
   "pedido": "Me mandem tudo o que vocês guardam sobre mim."
  },
  {
   "inciso": "III",
   "pedido": "Meu sobrenome está escrito errado no cadastro."
  },
  {
   "inciso": "IV",
   "pedido": "Vocês ainda guardam meu endereço de dez anos atrás, que não serve pra nada."
  },
  {
   "inciso": "V",
   "pedido": "Vou trocar de operadora e quero levar meus dados para lá."
  },
  {
   "inciso": "VI",
   "pedido": "Eu tinha autorizado, mudei de ideia: apaguem o que guardaram por causa disso."
  },
  {
   "inciso": "VII",
   "pedido": "Com quais empresas vocês compartilharam meus dados?"
  },
  {
   "inciso": "VIII",
   "pedido": "Se eu não autorizar o uso para marketing, perco o serviço?"
  },
  {
   "inciso": "IX",
   "pedido": "Não quero mais que usem meus dados para publicidade."
  },
  {
   "inciso": "II",
   "pedido": "Quero ver exatamente quais informações minhas aparecem no sistema de vocês."
  },
  {
   "inciso": "III",
   "pedido": "Mudei de telefone e o antigo continua no cadastro."
  },
  {
   "inciso": "I",
   "pedido": "Fiz uma compra aí em 2019. Sobrou algum registro meu?"
  }
 ]
}
;
