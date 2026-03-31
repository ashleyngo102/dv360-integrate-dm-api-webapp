import pandas as pd

try:
    df = pd.read_csv("/Users/ashleyngo/Downloads/repo/dm-api-test/Mock_Data_Baby_Names_1500.csv")
    df_sub = df.head(100).copy()
    df_sub['last_name'] = df_sub['last_name'] + "_mapped"

    df_sub = df_sub.rename(columns={
        "email (raw)": "email",
        "phone (raw)": "phone"
    })

    df_sub.to_csv("/Users/ashleyngo/Downloads/repo/dm-api-test/integrate-dm-api/Mock_Data_Sheet_Mapping_100.csv", index=False)
    print("File Mock_Data_Sheet_Mapping_100.csv generated successfully in the integrate-dm-api folder!")
except Exception as e:
    print(f"An error occurred: {e}")
