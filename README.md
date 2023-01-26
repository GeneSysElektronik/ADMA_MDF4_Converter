# ADMA MDF4 Converter
Further Information can be found at the [GeneSys Technical Support Center](https://genesys-offenburg.de/support-center/). 

## Environment information
This setup was implemented and tested with the following conditions:
- Windows 10
- Python3

## Usage
1. The help function gives detailed information about the usable commands and features
```bash
h
```

2. For grouping the data channels in channel groups, use a XML file, that fits the used GeneSys data format. 
```bash
gsda-mdf-xml $PATH_TO_XML-FILE
```

If no channel groups are needed, xml can be set to none.
```bash
gsda-mdf-xml none
```

3. Convert single .gsda files to .mf4
```bash
gsda-mdf-file $PATH_TO_GSDA-FILE
```

4. Convert all .gsda files in specific directory to .mf4
```bash
gsda-mdf-dir $PATH_TO_DIRECTORY_WITH_GSDA-FILES
```

5. Convert single .mf4 files to .mat
```bash
mdf-mat-file $PATH_TO_MF4-FILE
```

6. Convert all .mf4 files in specific directory to .mat
```bash
mdf-mat-dir $PATH_TO_DIRECTORY_WITH_MF4-FILES
```

7. For closing the converter hit STRG+C or use 
```bash
q 
```