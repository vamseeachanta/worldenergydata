git rev-list --objects --all | \
git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
awk '$1 == "blob" && $3 >= 52428800' | \
sort -k3 -n
