Currently the init script works up until git clone is complete, then it stalls.

This the last log coming directly from peform_git_clone

`Updating files: 100% (470412/470412), done.`

I then exited the process manually after waiting about 15 minutes and got this:

```bash
Updating files: 100% (470412/470412), done.[ERROR] Fatal error during fetch.
[PROMPT] Delete /Users/mgluf/chromium_src and re-init? (Y/n) n
[INFO] User opted to inspect the partial clone. Aborting fetch.
```

I don't know python very well, but i'm not sure if we're handling the completion state at all or correctly.

