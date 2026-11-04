# Tutorial (`api.tutorial`)

## `set_done`

POST only. Marks one of the user's tutorial topics done, or not yet, and returns the list of topics now done. Requires the **Intelligence User** or **Intelligence Agent** role ([../setup/permissions.md](../setup/permissions.md)). See [../tutorial/structure.md](../tutorial/structure.md#done).

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `topic` | str | ✓ | A topic key from `public/js/tutorial/content.js`: lowercase letters, digits and hyphens, up to 40 |
| `done` | bool | ✗ | Default true; false marks it not yet done |

Keeps the 100 most recent topics.
