root_dir = '/Users/mark/Documents/Terminal evaluation report'

fn = '7.5799_2024_te_unep_spccm_msp_asia_pacific_ EE Lighting in Pakistan.pdf'

import pathlib
import fitz
import pandas as pd

fp = pathlib.Path(root_dir).joinpath(fn)

doc = fitz.open(fp)


table_data = []
header = None
start_page = 0
end_page = 0
for page in doc:
    # print(page)
    for table in page.find_tables():
        # display(table.to_pandas())
        rows = table.to_pandas()
        table_header = table.header.names

        if 'criterion' in [i.strip().lower() for i in table_header]:

            # print({"header": header, "table_header": table_header, "start_page": start_page, "end_page": end_page})
            if table_header != header:
                table_data.append(rows)
                start_page = page.number
                end_page = page.number
            else:
                table_data[-1] = pd.concat([table_data[-1], rows],
                                           axis=0)  # print("merged: ")  # display(table_data[-1])
            header = table_header
            end_page = page.number

print(table_data)