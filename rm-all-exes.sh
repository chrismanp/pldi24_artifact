#!/usr/bin/bash

# any test executables?
cn=`find cilk5 -name "*.*" -type f -executable -print | wc -l`
pb=`find pbbs_v2/ -name "*.*" -type f -executable -print | wc -l`
if [ "$cn$pb" == "00" ]; then
    echo "Nothing to delete"
    exit 0
fi
# list them
find cilk5 -name "*.*" -type f -executable -print
find pbbs_v2/ -name "*.*" -type f -executable -print
read -p "Please confirm deletion (yes/no): " ans
if [ "$ans" == "yes" ]; then
    # delete them
    find cilk5 -name "*.*" -type f -executable -exec /bin/rm "{}" \;
    find pbbs_v2/ -name "*.*" -type f -executable -exec /bin/rm "{}" \;
    echo "All removed"
else
    echo "Nothing done"
fi

    
