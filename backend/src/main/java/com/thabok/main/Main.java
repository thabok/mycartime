package com.thabok.main;

import com.thabok.webservice.WebService;
import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.servlet.DefaultServlet;
import org.eclipse.jetty.servlet.ServletContextHandler;
import org.eclipse.jetty.servlet.ServletHolder;

public class Main {

	public static void main(String[] args) throws Exception {
		new WebService();

//		Server server = new Server(80);
//
//		ServletContextHandler context = new ServletContextHandler();
//		context.setContextPath("/");
//		context.setResourceBase("frontend");
//		context.addServlet(new ServletHolder(DefaultServlet.class), "/");
//
//		server.setHandler(context);
//		server.start();
//		server.join();
	}
}
