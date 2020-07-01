tool
extends EditorScript
var Collector: SceneTree = load("Collector.gd").new()
# A list of directories to collect files from.
var directories := [
	# "res://addons/Rakugo/"
	"res://addons/Rakugo/lib",
	"res://addons/Rakugo/types",
	"res://addons/Rakugo/nodes",
	"res://addons/Rakugo/statements",
	"res://addons/Rakugo/types"
]

var single_files := [
	"res://addons/Rakugo/main.gd"
]

var prefix = "res://addons/Rakugo"
# If true, explore each directory recursively
var is_recursive: = false
# A list of patterns to filter files.
var patterns := ["*.gd"]
# Output path to save the class reference.
var save_path := "res://reference.json"

func _run() -> void:
	var files := PoolStringArray()
	files.append_array(single_files)

	for dirpath in directories:
		files.append_array(Collector.find_files(dirpath, patterns, is_recursive))

	var json : String = Collector.print_pretty_json(Collector.get_reference(files, false, prefix))
	Collector.save_text(save_path, json)
