package io;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.UnsupportedEncodingException;
import java.util.List;

import org.yaml.snakeyaml.DumperOptions;
import org.yaml.snakeyaml.Yaml;

import entities.Person;

public class ImportExport {
	
	
	public static void main(String[] args) throws IOException {
		String testFile = "C:/Users/thabo/Downloads/template.yaml";
		String testFile2 = "C:/Users/thabo/Downloads/out.yaml";
		List<Person> importedPersons = importPersons(testFile);
		
		export(importedPersons, testFile2);
	}
	
	private static void export(Object o, String path) throws IOException {
		File file = new File(path);
        FileWriter writer = new FileWriter(file);
        DumperOptions options = new DumperOptions();
        options.setPrettyFlow(true);
        Yaml yaml = new Yaml(options);
        yaml.dump(o, writer);
	}
	
	@SuppressWarnings("unchecked")
	public static List<Person> importPersons(String path) throws UnsupportedEncodingException  {
		Object load;
		try {
			File file = new File(path);
			InputStreamReader isr = new InputStreamReader(new FileInputStream(file), "utf-8");
			Yaml yaml = new Yaml();
			load = yaml.load(isr);
			if (load instanceof List) {
				return (List<Person>)(List<?>)load;
			}
		} catch (FileNotFoundException e) {
			e.printStackTrace();
		}
		return null;
	}

}