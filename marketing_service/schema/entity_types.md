# Entity Types

- Primary: `mk_post`  
  - `entity_type="mk_post"`
  - `entity_id` = `post_id` (BIGINT) as string when calling Core

- Secondary:
  - `mk_source` (`source_id`) — whitelist источников
  - `mk_clipping` (`clipping_id`) — заимствованные материалы/ссылки

Документы/медиа связываются через Core и биндинги к `mk_post` (см. вьюху `v_mk_post_docs`).
