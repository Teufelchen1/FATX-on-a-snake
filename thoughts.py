fs = FATX.fromPartition(string)

# Generic info about the partition
fs.status()
# Return available/free space on the partition
fs.free()

# Returns a ff-object representing /
root = fs.getRoot()


# Returns a [ff-object,''] of all files & dirs in / 
root.ls()
root.ls('/')
# Returns a list of all files & dirs in /foo/bar
root.ls('/foo/bar')
# Returns a dict of all files & dirs in /
# with all details and values
root.ls('/', detail=true)

# returns the parent ff-obj(if any, otherwise returns itself)
root.parent()

# Returns a ff-object
obj = root.get('/') # can point to dir and file
