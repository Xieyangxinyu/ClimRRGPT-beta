import pandas as pd

def categorize_fwi(value):
        """Categorize the FWI value into its corresponding class and return the value and category."""
        if value <= 9:
            return 'Low'
        elif value <= 21:
            return 'Medium'
        elif value <= 34:
            return 'High'
        elif value <= 39:
            return 'Very High'
        elif value <= 53:
            return 'Extreme'
        else:
            return 'Very Extreme'
    
def fwi_color(value):
    fwi_class_colors = {
        'Low': 'rgb(255, 255, 0, 0.5)',
        'Medium': 'rgb(255, 204, 0, 0.5)',
        'High': 'rgb(255, 153, 0, 0.5)',
        'Very High': 'rgb(255, 102, 0, 0.5)',
        'Extreme': 'rgb(255, 51, 0, 0.5)',
        'Very Extreme': 'rgb(255, 0, 0, 0.5)'
    }
    return fwi_class_colors[categorize_fwi(value)]

def subset_by_crossmodel(df, crossmodel):
    subset = df[df['Crossmodel'] == crossmodel].iloc[0]
    return subset

def convert_to_dataframe(df, values_of_interests, crossmodels):
    data_dict = {}
    for crossmodel in crossmodels['Crossmodel']:
        value = df[df['Crossmodel'] == crossmodel].iloc[0]
        data_dict[crossmodel] = value

    data_rows = []

    columns = ['Crossmodel'] + values_of_interests
    
    for crossmodel, index_values in data_dict.items():
        row = [crossmodel]
        
        row += [index_values[key] for key in values_of_interests]
        
        data_rows.append(row)
    
    df = pd.DataFrame(data_rows, columns=columns)
    return df