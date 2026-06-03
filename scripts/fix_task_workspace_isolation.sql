-- Заявка «Привет» (ID 27) и прочие заявки с workspace_id автора
UPDATE tasks
SET workspace_id = u.workspace_id
FROM users u
WHERE tasks.created_by_id = u.id
  AND u.workspace_id IS NOT NULL
  AND (tasks.workspace_id IS DISTINCT FROM u.workspace_id);

-- Точечно: заявка «Привет» директора ООО «Отмена» (workspace_id = 2)
UPDATE tasks
SET workspace_id = 2
WHERE id = 27 OR title ILIKE 'Привет';
