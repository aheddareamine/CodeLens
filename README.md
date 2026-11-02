# CodeLens

## Chunking Strategy
### Python strategy
the default behavior if the max_chunk_size is big enough is to read imports, whole classes, whole functions and assignements, each on its own for import if too big for the max_size i'll priotize not to cut in the middle of a line
then continue the rest of imports in the second chunk or the next if there is too many for the chunk size
for classes i'd seperate by functions and try to keep the function definition and the docs for it together otherwise i'll split by returning to lines again also for functions if too long i'll prioritize splitting the function definition and its docs strring from the code then even if the code is too long i'll split with new lines so that i don't add half a line to the reterival and 