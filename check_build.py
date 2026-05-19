import urllib.request, json
url = "https://api.github.com/repos/rambochai7750973-hash/snakegame/actions/runs?per_page=3&status=in_progress"
data = json.loads(urllib.request.urlopen(url).read())
if data['workflow_runs']:
    for r in data['workflow_runs']:
        print(f"IN PROGRESS: {r['id']} | {r['created_at'][:19]}")
else:
    # Check most recent
    url = "https://api.github.com/repos/rambochai7750973-hash/snakegame/actions/runs?per_page=1"
    data = json.loads(urllib.request.urlopen(url).read())
    r = data['workflow_runs'][0]
    print(f"Latest: {r['id']} | {r['status']} | {str(r['conclusion'])} | {r['created_at'][:19]}")
