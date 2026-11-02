# Examples

Each script makes one real OpenAI call and records its usage in Ganivra.

```bash
python -m pip install ganivra openai
export GANIVRA_API_KEY=your_ganivra_key
export OPENAI_API_KEY=your_openai_key
python examples/simple_openai.py
```

- `simple_openai.py`: initialize Ganivra, then use the OpenAI client as usual.
- `traced_openai.py`: attach a workflow, feature and customer to the call so
  its cost shows up per customer.
