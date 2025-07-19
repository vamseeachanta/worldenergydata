
Action Items:

- [] unit test opp.py

I found 2 references to get_time_series_from_orcaflex_run in opp.py:

In the post_process_RAOs method:
In the get_time_series_output method:
Both of these calls are now properly delegated to the OPPTimeSeries class through the delegate method we added:

I didn't find any other references to this function outside of opp.py. The refactoring appears to be complete and all dependencies have been properly updated.

Would you like me to look for any other potential references or make any additional changes?

# Refactor this Function

refacor this function
move to module opp_time_series, class OPPTimeSeries, new function

Mandatory instructions:
follow coding conventions in module opp.py
do not make all the changes at once
analyze all dependencies in code base
confirm the list of changes to opp_time_series.py, opp.py, any other impacted files anywhere in the code base
make changes one by one after receiving confirmation for each

### Lang Chain AI

https://python.langchain.com/docs/concepts/prompt_templates/
https://github.com/langchain-ai/langchain
https://medium.com/@ssmaameri/prompt-templates-in-langchain-efb4da260bd3
https://github.com/preset-io/promptimize/blob/main/examples/python_examples.py