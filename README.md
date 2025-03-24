# ppdf

> [!CAUTION]
>
> Work in progress. (See: [Road-map](#road-map))

Playwright to PDF.

Roughly based on wget:

```bash
ppdf -rl 2 -A http:*//example.com/*/ -o output.pdf
```

### Road-Map:

- [x] Command-line interface. _(mostly complete)_
- [x] Capture recursion.
- [ ] Capture annotation linking. _(modify link annotations to point locally)_
- [ ] ZipApp & PyInstaller.
