# Política: a lei tem um dono, e não é esta suíte

**A regra.** O texto da LGPD, a atribuição de guardião por artigo e a cor canônica de cada
um vêm de `danzeroum/guardioes-governanca`, no commit que `lei.lock` ancora. São
materializados em `workspace/lei/` e conferidos por sha256 a cada execução.

**Por que não copiar.** Uma cópia com uma linha removida faz o validador dizer "nenhum
achado" — sem erro, sem aviso, indistinguível de um roteiro correto. A cópia derivaria em
silêncio, e o filme passaria a ensinar uma lei que ninguém escreveu. Num material
educativo sobre a lei, isso não é um detalhe de arquitetura.

**Por que conferir o hash.** Materializar sem conferir seria uma cópia com um passo extra:
se a origem mudasse embaixo da âncora, o validador mediria os roteiros contra uma lei que
ninguém declarou — e diria "tudo certo", porque de fato estaria tudo certo contra a lei
errada.

**Avançar a âncora é change-proposal.** Pode mudar o que um filme já publicado afirma.

---
Fiscalizado por: `estudio_suite/lei.py:materializar()`, em todo `validar_tudo`.
Falha como: `ErroDeDados` e **exit 2** — não 1. "Estou sem a lei" e "o roteiro está errado"
são estados diferentes; colapsá-los faz a leitura barata vencer: *deve ser a rede*.
