# Publishing NuVCFtools benchmarks

Edit `benchmarks/published.json` to change the numbers on the BioCode Commons website. Open a pull request, wait for **Published benchmark** to validate it, and merge to `main`. GitHub Actions then asks the website to publish the updated table. Editing the README alone does not trigger publication.

- For the first result, replace the entire `unpublished` record with a measured record. Use the [publication format](https://github.com/BioCode-Commons/BioCode-Commons.github.io/blob/main/benchmarks/README.md) and an [existing record](https://github.com/BioCode-Commons/NuSTAR/blob/main/benchmarks/published.json) as references.
- Commit the benchmark report before preparing the data file so `evidence_url` can point to the report at its full commit SHA. Identify both executable revisions, input, machine, threads, repetitions, output checks, and what each timer and memory measurement covers.
- Enter a row for each published dataset/task and resource setting. Use seconds for wall time and the declared MiB or GiB for peak memory. Keep any index-build measurements separate from sample runs. The website calculates ratios from the measurements.
- Update the benchmark section of the README when publishing the first results. Until then, keep the explicit `unpublished` state. Never enter dummy values to make a table appear.
- To check delivery, follow **Published benchmark** here, then [Publish benchmark tables](https://github.com/BioCode-Commons/BioCode-Commons.github.io/actions/workflows/benchmarks.yml) on the website. The organization manages the publishing App. Maintainers do not need a personal token.
