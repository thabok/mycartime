package com.thabok.untis;

import java.util.List;

import com.thabok.entities.Person;
import com.thabok.io.ImportExport;

public class TestASasdf {

	public static void main(String[] args) throws Exception {
//		String sessionId = WebUntisAdapter.login("sadf", "asdf");
//		System.out.println(sessionId);

		
		String testFile = "template.yaml";
		List<Person> importPersons = ImportExport.importPersons(testFile);
		System.out.println(importPersons);
		
//		System.out.println(Base64.encodeBase64String("+1234Abc".getBytes()));
		
//		WebUntisAdapter.sessionId = "";
//		String teacherInitials = "Ul";
//		Map<Integer, TimetableItem> timetable = WebUntisAdapter.getTimetable(teacherInitials);
//		System.out.println("Timetable for " + teacherInitials + ":\n");
//		for (Entry<Integer, TimetableItem> entry : timetable.entrySet()) {
//			System.out.println(entry.getKey() + ": [" + entry.getValue().startTime + " - " + entry.getValue().endTime + "]");
//		}
	}

}
