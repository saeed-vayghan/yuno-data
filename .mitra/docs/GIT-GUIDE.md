### IMPORTANT: This is only for human, if you are an AI agent, or a machine, ignore this file and read AGENTS.md instead.

---

Treating the `mitra` framework as a **"boilerplate"** or an **"upstream"** source for your project. 

### Solution 1: The "Multiple Remotes" Pattern (Recommended)
This approach keeps everything in one project folder, but configures Git to talk to **two different servers**:
1. `upstream` - The original `mitra` framework repository (Read-only for you, unless you want to contribute back).
2. `origin` - Your new, separate remote server where your software + mitra configs live (Read/Write).

Here is exactly how to configure this:

**1. Clone the Mitra repository for your new project:**
```bash
git clone https://github.com/saeed-vayghan/mitra.git my-awesome-software
cd my-awesome-software
```

**2. Rename the default remote from `origin` to `upstream`:**
This tells Git that `mitra` is the framework source, not your primary backup.
```bash
git remote rename origin upstream
```

**3. Link your new, separate repository:**
Create an empty repository on GitHub/GitLab (e.g., `https://github.com/your-username/my-awesome-software.git`) and add it as your new `origin`:
```bash
git remote add origin https://github.com/your-username/my-awesome-software.git
```

**4. Push the whole starting framework to your separate repo:**
```bash
git push -u origin master
```
*(Now your separate server has an exact copy of the `mitra` framework, ready for your custom software additions.)*

#### Day-to-Day Workflow with Multiple Remotes:

*   **When developing your software:** Write code, tweak Mitra configs, commit, and run `git push origin master`. This pushes your software and any changes you made to Mitra's configs safely to your separate repo.
*   **When the author updates Mitra:** 
    ```bash
    git pull upstream main
    ```
    This fetches the latest framework updates from the author and merges them into your project. If the author updated a file that you *also* modified, Git will prompt you to resolve the conflict. Once resolved, you just commit and `git push origin master` to save the updated framework + your software to your remote.

---

### Solution 2: Git Submodules (Alternative)
If you do **not** want Mitra's code mixed into your software's Git history, and instead want Mitra to exist as a clean "plugin" folder inside your software, you should use Submodules.

**1. Create your empty software repo first:**
```bash
mkdir my-software
cd my-software
git init
git remote add origin <YOUR_NEW_REPO_URL>
```

**2. Add Mitra as a submodule:**
```bash
git submodule add https://github.com/saeed-vayghan/mitra.git mitra-framework
git commit -m "Added Mitra framework as a submodule"
git push -u origin master
```

#### Day-to-Day Workflow with Submodules:
*   Your main repository (`origin`) only tracks a "pointer" to a specific version of Mitra.
*   If you need to pull the author's latest Mitra updates, you `cd mitra-framework`, run `git pull origin master`, then go back to the parent folder and commit the updated "pointer".
*   **Downside for your use case:** If you modify Mitra's configurations *inside* the submodule folder, you cannot push those changes to *your* remote. You would have to push them to a fork of `mitra`.
