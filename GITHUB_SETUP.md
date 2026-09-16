# GitHub setup

Create an empty GitHub repository, for example:

```text
personal-photo-toolkit
```

Then from this project folder:

```bash
git init
git add .
git commit -m "Initial cross-platform photo toolkit"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/personal-photo-toolkit.git
git push -u origin main
```

## Let other people improve it

For a public repository, contributors can fork the project and open pull requests.

For selected collaborators who should push directly:

1. Open the repository on GitHub.
2. Go to **Settings**.
3. Open **Collaborators** / **Access**.
4. Invite the person.

Before every push, check:

```bash
git status
```

Make sure no personal photos, videos, Google Takeout files or generated output folders are staged.
