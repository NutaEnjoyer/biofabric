# Function-by-Function Notes (Human descriptions)

## marketing/app.py
- Registers API routers for posts, sources, AI, calendar.

## marketing/config.py
- `Settings`: loads env vars; stores tokens and URLs.
- `DEFAULT_FORMATS`: default list for validation hints.

## marketing/db.py
- `engine`, `SessionLocal`: async SQLAlchemy engine and session factory.
- `metadata`: shared MetaData used for reflection.
- `get_session()`: yields AsyncSession per request.

## marketing/common/logging.py
- `log_event(event, **fields)`: simple structured STDOUT logger.

## marketing/common/errors.py
- `Forbidden`, `NotFound`, `BadRequest`: HTTPException helpers.

## marketing/common/correlation.py
- `correlation_id(...)`: returns/creates X-Correlation-Id.

## marketing/core_client/client.py
- `CoreClient.advance_workflow(...)`: move workflow in Core.
- `CoreClient.bind_document(...)`: link a document to entity in Core.
- `CoreClient.audit(...)`: write audit message to Core.

## marketing/api/deps.py
- `get_db()`: yields DB session.
- `get_core()`: returns CoreClient with correlation id.
- `get_user()`: dummy user (to be replaced with real auth).

## marketing/security/rbac.py
- `can(user, action, resource)`: minimal role-based checks.

## marketing/schemas/dto_common.py
- `ResponseOk`, `ErrorResponse`: standard API envelopes.

## marketing/schemas/dto_posts.py
- `PostCreate`, `PostUpdate`, `PostRead`: DTOs for post CRUD.
- `PublishNowRequest/Response`: DTOs for manual publish.
- `ReplacePostRequest`: DTO for calendar replacement.

## marketing/schemas/dto_sources.py
- `SourceCreate/Read`: DTOs for whitelist sources.
- `FetchMaterialsRequest`: instruct to fetch 10 materials per source.

## marketing/schemas/dto_ai.py
- `PlanFromPromptRequest/Result`: AI plan generation.
- `IdeasFromSourcesRequest/Result`: ideas from sources.

## marketing/repositories/posts_repo.py
- `create_draft_post(...)`: inserts into mk_posts + mk_post_contents.
- `get_post(...)`: returns post + content.
- `list_posts(...)`: filtering by period.
- `update_post(...)`: updates meta/content.
- `set_status(...)`, `set_date(...)`, `set_external_url(...)`: field updates.

## marketing/repositories/sources_repo.py
- `create(...)`, `list(...)`, `delete(...)`: manage mk_sources.
- `get_last_10(...)`: placeholder for fetch logic (parser lives elsewhere).

## marketing/repositories/calendar_repo.py
- `calendar(...)`: posts with dates for a period.
- `ideas_bucket(...)`: posts without date (ideas).

## marketing/services/posts.py
- `create_draft(...)`: high-level creation with validation.
- `get(...)`, `update(...)`: fetch and update card.
- `set_status(...)`, `set_date(...)`, `set_external_url(...)`: business wrappers.
- `replace_post_in_plan(...)`: safe swap of planned post with idea.

## marketing/services/publishing.py
- `publish_now_tg(text)`: Telegram sendMessage call, returns URL.
- `publish_now_vk(text)`: VK wall.post, returns URL.

## marketing/services/workflow.py
- `advance(...)`: Core workflow transition wrapper.

## marketing/services/documents.py
- `bind(...)`: attach document in Core to mk_post.

## marketing/services/ai_plan.py
- `generate_from_prompt(...)`: creates 3 draft posts based on prompt (MVP stub).

## marketing/services/ai_sources.py
- `ideas_from_sources(...)`: for each source, creates up to 10 idea drafts (MVP stub).

## marketing/api/router_posts.py
- `create_post(...)`: create draft.
- `get_post(...)`: read card.
- `list_posts(...)`: list.
- `update_post(...)`: update.
- `set_status(...)`: change status (also notify Core).
- `set_date(...)`: assign date (manual).
- `publish_now(...)`: manual publish to TG/VK, set published + URL.
- `replace_post(...)`: swap planned post with idea.

## marketing/api/router_sources.py
- `add_source(...)`: create source.
- `list_sources(...)`: list sources.
- `delete_source(...)`: remove source.
- `fetch_materials(...)`: placeholder for 10 latest materials.

## marketing/api/router_ai.py
- `ai_generate_plan(...)`: AI plan generation from prompt (no dates).
- `ai_generate_ideas(...)`: AI ideas from sources (10 per source).

## marketing/api/router_calendar.py
- `calendar(...)`: simple “when & what” view.
- `ideas_bucket(...)`: ideas without dates.
