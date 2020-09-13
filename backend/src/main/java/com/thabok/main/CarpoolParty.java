package com.thabok.main;

import java.io.UnsupportedEncodingException;
import java.util.List;

import com.thabok.entities.Person;
import com.thabok.entities.WeekPlan;
import com.thabok.io.ImportExport;


public class CarpoolParty {

	private static Controller controller;

	public static void main(String[] args) throws Exception {
		initializeController();
		calculate(1000);
	}
	
	private static void calculate(int iterations) throws Exception {
		System.out.println();
		System.out.println("Result after " + iterations + " iterations:");
		WeekPlan goodPlan = controller.calculateGoodPlan(iterations);
		controller.getFitness(goodPlan, true);
		String noDrivesSummary = controller.summarizeNumberOfDrives(goodPlan);
		System.out.println(goodPlan);
		System.out.println(goodPlan.getWeekDayPermutation());
	}
	
	private static void initializeController() throws UnsupportedEncodingException {
		String testFile = "template.yaml";
		List<Person> importPersons = ImportExport.importPersons(testFile);
		controller = new Controller(importPersons);
	}
	
}
