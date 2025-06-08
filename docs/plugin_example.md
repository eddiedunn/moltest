# Plugin Example

MolTest can be extended by loading Python modules that define optional hook functions.
The CLI looks for entry points under the group `moltest.plugins` and for module
names listed in the user's configuration file under the `plugins` key.

Plugins can implement any of the following hooks:

- `before_run(ctx)` – called right after plugins are loaded.
- `after_run(results)` – called before the process exits with the list of scenario results.
- `before_scenario(scenario_id)` – called before each scenario is executed.
- `after_scenario(scenario_id, status)` – called after each scenario completes.

```python
# my_plugin.py
from typing import List

events: List[str] = []

def before_run(ctx):
    events.append("before_run")

def before_scenario(scenario_id):
    events.append(f"before:{scenario_id}")

def after_scenario(scenario_id, status):
    events.append(f"after:{scenario_id}:{status}")

def after_run(results):
    events.append("after_run")
```

Add `"my_plugin"` to the `plugins` list in your `~/.config/moltest/config.json`
(or expose it via a `moltest.plugins` entry point) and the hook functions will be
invoked during `moltest run`.
