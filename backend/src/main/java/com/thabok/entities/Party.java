package com.thabok.entities;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

public class Party {

	private DayOfWeekABCombo dayOfWeekABCombo;
	private boolean isWayBack;
	private Person driver;
	private int time;
	private int lesson;
	private List<Person> passengers = new ArrayList<>();

	public Person getDriver() {
		return driver;
	}

	public int getLesson() {
		return lesson;
	}

	public void setLesson(int lesson) {
		this.lesson = lesson;
	}

	public int getTime() {
		return time;
	}

	public void setTime(int time) {
		this.time = time;
	}

	public void setDriver(Person driver) {
		this.driver = driver;
	}

	public List<Person> getPassengers() {
		return passengers;
	}
	
	public Person popPassenger() {
		if (!passengers.isEmpty()) {
			Person removedPassenger = passengers.remove(passengers.size() - 1);
			updateTime();
			return removedPassenger;
		}
		throw new IllegalStateException("Cannot remove passengers because... there are none.");
	}

	/**
	 * Updates the party time to the earliest time (if wayThere) or the latest time (if wayBack) of any member (driver/passengers).
	 */
	private void updateTime() {
		int updatedTime;
		if (this.isWayBack) {
			updatedTime = driver.schedule.get(dayOfWeekABCombo.getUniqueNumber()).getEndTime();
			for (Person passenger : this.passengers) {
				int passengerTime = passenger.schedule.get(dayOfWeekABCombo.getUniqueNumber()).getEndTime();
				updatedTime = Math.max(updatedTime, passengerTime);
			}
		} else {
			updatedTime = driver.schedule.get(dayOfWeekABCombo.getUniqueNumber()).getStartTime();
			for (Person passenger : this.passengers) {
				int passengerTime = passenger.schedule.get(dayOfWeekABCombo.getUniqueNumber()).getStartTime();
				updatedTime = Math.min(updatedTime, passengerTime);
			}
		}
		this.time = updatedTime;
		
	}

	/**
	 * Sets passengers. If this list contains the driver he will be ignored
	 * @param passengers
	 * @throws Exception if you try to add too many people
	 */
	public void setPassengers(List<Person> passengers) throws Exception {
		this.passengers = passengers;
		try {
			if (this.passengers.contains(driver)) {
				this.passengers.remove(driver);
			}
		} catch (Exception e) {
		}
		this.updateTime();
	}
	
	/**
	 * Adds the passenger to the party and adapts the parties time if needed (can happen due to supervisions).
	 * 
	 * @param p the passenger to add to the party
	 */
	public void addPassenger(Person p) {
		if (passengers.size() >= driver.getNoPassengerSeats()) {
			throw new IllegalStateException("Cannot add a passenger to " + driver + "'s car, it's already full!");
		}
		this.passengers.add(p);
		this.updateTime();
	}

	public DayOfWeekABCombo getDayOfTheWeekABCombo() {
		return dayOfWeekABCombo;
	}

	public void setDayOfTheWeekABCombo(DayOfWeekABCombo dayOfWeekABCombo) {
		this.dayOfWeekABCombo = dayOfWeekABCombo;
	}

	public boolean isWayBack() {
		return isWayBack;
	}

	public void setWayBack(boolean isWayBack) {
		this.isWayBack = isWayBack;
	}

	public String toString() {
		return (isWayBack ? "[<-] " : "[->] ")
				+ "[" + getLessonAsTwoCharacters() +  "] "
				+ driver.getName()
				+ (passengers.isEmpty() ? "" : " (" + String.join(", ", passengers.stream().map(p -> p.getName()).collect(Collectors.toList())) + ")");
	}
	
//	public int getLesson() {
//		if (isWayBack) {
//			// way back
//			return driver.schedule.get(dayOfWeekABCombo.getUniqueNumber()).getLastLesson();
//		} else {
//			// way there
//			return driver.schedule.get(dayOfWeekABCombo.getUniqueNumber()).getFirstLesson();
//		}
//	}
//	
	public String getLessonAsTwoCharacters() {
		int lesson = getLesson();
		if (lesson < 10) {
			return " " + lesson;
		} else {
			return "" + lesson;
		}
	}

	public void removePassenger(Person swapper) {
		this.passengers.remove(swapper);
		updateTime();
		
	}
}
