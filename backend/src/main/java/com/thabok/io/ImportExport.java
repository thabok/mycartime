package com.thabok.io;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.InputStreamReader;
import java.io.UnsupportedEncodingException;
import java.util.List;

import org.yaml.snakeyaml.Yaml;

import com.thabok.entities.Person;



public class ImportExport {
	
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