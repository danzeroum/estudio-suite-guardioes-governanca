# Política: a orientação deriva; ela não descreve

**A regra.** Os blocos `<!-- DERIVADO:… -->` do README e o `catalogo.js` são **gerados** do
estado vivo. Nenhuma lista de rigs, poses, cenários ou filmes é escrita à mão.

**Por que um guia seria a solução errada.** Um README que enumera é uma segunda descrição
do repositório. Segunda descrição deriva da primeira — em silêncio, sem erro, e com a
aparência de documentação cuidadosa. Alguém acrescenta uma pose, ninguém lembra do README,
e o README passa a ensinar um estúdio que não existe mais. Com confiança.

**E a orientação de verdade manda perguntar.** `estudio orientar` e `estudio inventario`
leem o estado agora. A primeira seção do README diz para não confiar nas tabelas do próprio
README — o que soa estranho até se perceber que é a única forma de elas continuarem certas.

---
Fiscalizado por: `ci/sincronizar_derivados.py --check`, dentro de `validar_tudo`.
Falha como: **exit 1**, nomeando o artefato fora de dia e o comando que o regrava.
Mesmo passo "artefato gerado está em dia" que o repositório de origem já roda.
