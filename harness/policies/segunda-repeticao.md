# Política: adereço sobe ao elenco no segundo uso, não no primeiro

**A regra.** O que uma história pede e não existe nasce em `filmes/<id>/local/`. Subir ao
elenco compartilhado exige prova de **segundo uso**, e quem abre a proposta é o `curador`.

**Por que não no primeiro.** Uma história não é evidência de que algo é geral. Promover na
primeira vez produz um elenco que é a união de todos os casos particulares — e cada um com
o formato que a história daquele dia pedia.

**Por que não deixar copiar.** Um fiscal proíbe um filme de referenciar o `local/` de
outro. Sem essa proibição, o mesmo adereço nasce cinco vezes ligeiramente diferente e
nenhuma versão é a certa.

**O que muda em relação a lembrar da regra.** Nada, exceto que o módulo **conta**. A regra
"abstração só nasce na segunda repetição" sempre esteve escrita; o que faltava era alguém
percebendo a segunda repetição no dia em que ela acontece.

---
Fiscalizado por: `estudio_suite/melhorias/evidencias.py:promocoes()`.
Provado por: `tests/test_melhorias.py`, nos **dois** sentidos — um filme só não propõe,
dois propõem. Propositor que nunca propôs não provou nada.
